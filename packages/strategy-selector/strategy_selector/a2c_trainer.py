"""QTMRL 轻量级 A2C (Advantage Actor-Critic) 在线训练器。

基于 QTMRL（Quantitative Trading with Multi-Indicator Guided Reinforcement
Learning）论文框架的工程化实现。不依赖 PyTorch/TensorFlow，使用纯 NumPy 在
每个 /settle 周期执行增量式在线学习。

核心设计：
- 状态空间：factor-engine 输出的多维技术指标向量（趋势/波动率/动量/资金流）
- 策略网络（Actor）：输出资产配置方向权重（long/short/neutral 三分量 softmax）
- 价值网络（Critic）：评估当前状态的市场潜力标量
- 奖励信号：来自 FinPos 复合得分（即时 PnL + 短期/中期夏普 + 回撤惩罚）

与静态 policy_blender 的关系：
- 当 A2C 网络未充分训练（episode < 10）时，回退到 policy_blender 的确定性逻辑
- 当训练成熟后，A2C 的 actor 输出替代 policy_blender 的线性融合
- Critic 输出始终作为附加风险信号注入 selector 的 confidence 调节
"""

from __future__ import annotations

import math
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class A2CConfig:
    """A2C 超参数配置。"""

    # 网络结构
    state_dim: int = 10  # 与 policy_blender.build_state_vector 对齐
    action_dim: int = 3  # long / short / neutral
    hidden_dim: int = 16

    # 学习率
    actor_lr: float = 0.005
    critic_lr: float = 0.01
    gamma: float = 0.92  # 折扣因子

    # 探索
    entropy_coef: float = 0.08  # 熵奖励系数，鼓励探索

    # 训练门控
    min_episodes_before_active: int = 10  # 最少需要多少次训练后才接管
    max_episodes_memory: int = 200  # 保留最近 N 次 episode 用于批量回放

    # 持久化
    checkpoint_path: str = "data/a2c_checkpoint.json"

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_dim": self.state_dim,
            "action_dim": self.action_dim,
            "hidden_dim": self.hidden_dim,
            "actor_lr": self.actor_lr,
            "critic_lr": self.critic_lr,
            "gamma": self.gamma,
            "entropy_coef": self.entropy_coef,
            "min_episodes_before_active": self.min_episodes_before_active,
        }


def _relu(x: float) -> float:
    return max(0.0, x)


def _softmax(logits: list[float]) -> list[float]:
    """数值稳定的 softmax。"""
    max_logit = max(logits)
    exps = [math.exp(x - max_logit) for x in logits]
    total = sum(exps)
    if total == 0:
        return [1.0 / len(logits)] * len(logits)
    return [e / total for e in exps]


def _tanh_clip(x: float) -> float:
    """tanh 夹紧到 [-1, 1]，溢出时裁剪。"""
    return max(-1.0, min(1.0, math.tanh(x)))


def _init_weights(rows: int, cols: int, scale: float = 0.1) -> list[list[float]]:
    """Xavier 风格的均匀初始化（简化版）。"""
    import random
    bound = scale * math.sqrt(6.0 / (rows + cols))
    return [[random.uniform(-bound, bound) for _ in range(cols)] for _ in range(rows)]


def _zeros_vec(size: int) -> list[float]:
    return [0.0] * size


def _zeros_mat(rows: int, cols: int) -> list[list[float]]:
    return [[0.0] * cols for _ in range(rows)]


def _dot_vec(v1: list[float], v2: list[float]) -> float:
    return sum(a * b for a, b in zip(v1, v2))


def _mat_vec_mul(mat: list[list[float]], vec: list[float]) -> list[float]:
    return [_dot_vec(row, vec) for row in mat]


def _vec_add(v1: list[float], v2: list[float]) -> list[float]:
    return [a + b for a, b in zip(v1, v2)]


def _vec_scale(v: list[float], s: float) -> list[float]:
    return [x * s for x in v]


def _outer_product(v1: list[float], v2: list[float]) -> list[list[float]]:
    return [[x * y for y in v2] for x in v1]


class A2CTrainer:
    """轻量级在线 A2C 训练器。

    在每个 /settle 周期调用 step() 完成：
    1. 根据上次的 (state, action) 和当前奖励 计算 TD 误差
    2. 更新 Critic 网络（价值估计）
    3. 计算 Advantage，更新 Actor 网络（策略梯度）
    4. 将当前状态-动作对保存为下一轮的前置上下文

    Usage::

        trainer = A2CTrainer(config)
        # 在 select_strategy 中
        action = trainer.act(state_vector)  # 或 fallback 到 policy_blender
        # 在 /settle 中
        trainer.step(current_state, action_idx, finpos_composite_score)
    """

    def __init__(self, config: A2CConfig | None = None, checkpoint_dir: str = "data"):
        self.cfg = config or A2CConfig()
        self.cfg.checkpoint_path = str(Path(checkpoint_dir) / "a2c_checkpoint.json")

        # 网络权重
        # Actor: state_dim -> hidden_dim -> action_dim
        # Critic: state_dim -> hidden_dim -> 1
        self.actor_w1 = _init_weights(self.cfg.hidden_dim, self.cfg.state_dim)
        self.actor_b1 = _zeros_vec(self.cfg.hidden_dim)
        self.actor_w2 = _init_weights(self.cfg.action_dim, self.cfg.hidden_dim)
        self.actor_b2 = _zeros_vec(self.cfg.action_dim)

        self.critic_w1 = _init_weights(self.cfg.hidden_dim, self.cfg.state_dim)
        self.critic_b1 = _zeros_vec(self.cfg.hidden_dim)
        self.critic_w2 = _init_weights(1, self.cfg.hidden_dim)
        self.critic_b2 = [0.0]

        # 训练状态
        self.episode_count: int = 0
        self.total_steps: int = 0
        self.prev_state: list[float] | None = None
        self.prev_action_idx: int | None = None
        self.prev_critic_value: float = 0.0
        self.last_td_error: float = 0.0  # 最近的 TD 误差
        self.last_advantage: float = 0.0  # 最近的优势函数值
        self.last_policy_entropy: float = 0.0  # 最近策略熵

        # 尝试从检查点恢复
        self._try_load()

    # ------------------------------------------------------------------
    # 前向传播
    # ------------------------------------------------------------------

    def _forward_actor(self, state_vec: list[float]) -> tuple[list[float], list[float], float]:
        """Actor 前向传播 → (action_probs, logits, entropy)。"""
        # hidden = relu(W1 * state + b1)
        hidden_raw = _vec_add(_mat_vec_mul(self.actor_w1, state_vec), self.actor_b1)
        hidden = [_relu(x) for x in hidden_raw]
        # logits = W2 * hidden + b2
        logits = _vec_add(_mat_vec_mul(self.actor_w2, hidden), self.actor_b2)
        probs = _softmax(logits)
        # 熵 = -sum(p * log(p))
        entropy = 0.0
        for p in probs:
            if p > 1e-12:
                entropy -= p * math.log(p)
        return probs, hidden, entropy

    def _forward_critic(self, state_vec: list[float]) -> tuple[float, list[float]]:
        """Critic 前向传播 → (value, hidden)。"""
        hidden_raw = _vec_add(_mat_vec_mul(self.critic_w1, state_vec), self.critic_b1)
        hidden = [_relu(x) for x in hidden_raw]
        raw_value = _dot_vec(self.critic_w2[0], hidden) + self.critic_b2[0]
        value = _tanh_clip(raw_value)
        return value, hidden

    # ------------------------------------------------------------------
    # 行动接口
    # ------------------------------------------------------------------

    def act(self, state_vec: list[float], deterministic: bool = False) -> dict[str, Any]:
        """给定状态向量，采样或确定性地选择一个动作。

        Args:
            state_vec: policy_blender.build_state_vector 输出的 10 维向量
            deterministic: True 时直接取 argmax (inference mode)

        Returns:
            {
                "action_idx": 0=long, 1=short, 2=neutral,
                "action_name": "long"|"short"|"neutral",
                "probs": [p_long, p_short, p_neutral],
                "critic_value": float,
                "entropy": float,
                "active": bool (是否足以替代 policy_blender),
            }
        """
        if len(state_vec) != self.cfg.state_dim:
            raise ValueError(
                f"state_dim mismatch: got {len(state_vec)}, expected {self.cfg.state_dim}"
            )

        probs, _actor_hidden, entropy = self._forward_actor(state_vec)
        critic_val, _critic_hidden = self._forward_critic(state_vec)

        active = self.episode_count >= self.cfg.min_episodes_before_active

        if deterministic:
            action_idx = max(range(len(probs)), key=lambda i: probs[i])
        else:
            # 按概率分布采样
            import random
            r = random.random()
            cumulative = 0.0
            action_idx = 0
            for i, p in enumerate(probs):
                cumulative += p
                if r <= cumulative:
                    action_idx = i
                    break

        action_map = {0: "long", 1: "short", 2: "neutral"}
        return {
            "action_idx": action_idx,
            "action_name": action_map.get(action_idx, "neutral"),
            "probs": probs,
            "critic_value": critic_val,
            "entropy": entropy,
            "active": active,
        }

    def critic_value(self, state_vec: list[float]) -> float:
        """快速获取 Critic 对当前状态的价值评估（用于 confidence 调节）。"""
        val, _ = self._forward_critic(state_vec)
        return val

    # ------------------------------------------------------------------
    # 学习步骤
    # ------------------------------------------------------------------

    def step(
        self,
        current_state: list[float],
        current_action_idx: int,
        reward: float,
        done: bool = True,
    ) -> dict[str, Any]:
        """执行一步 A2C 在线更新。

        调用时机：每次 /settle 结算后，用 finpos_rewards.composite_score 作为 reward。

        Args:
            current_state: 当前决策时的状态向量
            current_action_idx: 当前决策选择的动作索引 (0=long, 1=short, 2=neutral)
            reward: FinPos 复合得分（已归一化，范围约 [-1, 1]）
            done: 是否为 episode 终点 (单步交易默认为 True)

        Returns:
            训练指标摘要，包含 td_error, advantage, losses 等
        """
        # 如果没有先前状态（首个 episode），跳过更新
        if self.prev_state is None:
            prev_probs, _, entropy = self._forward_actor(current_state)
            prev_critic_val, _ = self._forward_critic(current_state)
            self.prev_state = current_state
            self.prev_action_idx = current_action_idx
            self.prev_critic_value = prev_critic_val
            self.last_policy_entropy = entropy
            self.episode_count += 1
            return {
                "step": self.episode_count,
                "td_error": 0.0,
                "advantage": 0.0,
                "actor_loss": 0.0,
                "critic_loss": 0.0,
                "entropy": entropy,
                "message": "First episode recorded; no gradient update yet.",
            }

        # -------- TD Error 与 Advantage 计算 --------
        current_critic_val, current_critic_hidden = self._forward_critic(current_state)
        # TD target: 如果是终止状态则只有 reward
        next_value = 0.0 if done else current_critic_val
        td_target = reward + self.cfg.gamma * next_value
        td_error = td_target - self.prev_critic_value
        advantage = td_error  # 简化版 A2C 使用 TD error 作为 advantage

        # -------- Critic 更新 (MSE loss) --------
        prev_critic_hidden_raw = _vec_add(
            _mat_vec_mul(self.critic_w1, self.prev_state), self.critic_b1
        )
        prev_critic_hidden = [_relu(x) for x in prev_critic_hidden_raw]
        # dLoss/dValue = -2 * (td_target - prev_value) = -2 * advantage
        critic_output_grad = -2.0 * advantage

        # 因为 value = tanh(raw)，所以 dValue/dRaw = 1 - tanh^2 = 1 - value^2
        prev_value_clipped = _tanh_clip(
            _dot_vec(self.critic_w2[0], prev_critic_hidden) + self.critic_b2[0]
        )
        d_tanh = 1.0 - prev_value_clipped * prev_value_clipped
        d_tanh = max(d_tanh, 1e-6)  # 防止梯度消失
        critic_raw_grad = critic_output_grad * d_tanh

        # critic_w2 梯度
        critic_w2_grad = [[critic_raw_grad * h] for h in prev_critic_hidden]
        # critic_b2 梯度
        critic_b2_grad = [critic_raw_grad]

        # critic_w1 和 b1 的梯度 (relu 反向传播)
        critic_hidden_grad = [critic_raw_grad * w for w in self.critic_w2[0]]
        for i in range(self.cfg.hidden_dim):
            # relu 导数: 1 if input > 0 else 0
            if prev_critic_hidden_raw[i] > 0:
                # dL/dW1[i][j] = hidden_grad[i] * state[j]
                for j in range(self.cfg.state_dim):
                    self.critic_w1[i][j] -= self.cfg.critic_lr * critic_hidden_grad[i] * self.prev_state[j]
                self.critic_b1[i] -= self.cfg.critic_lr * critic_hidden_grad[i]
            else:
                pass  # relu 梯度为 0，权重不更新

        # 更新 critic_w2 和 b2
        for i in range(self.cfg.hidden_dim):
            self.critic_w2[0][i] -= self.cfg.critic_lr * critic_w2_grad[i][0]
        self.critic_b2[0] -= self.cfg.critic_lr * critic_b2_grad[0]

        critic_loss = advantage * advantage  # MSE loss

        # -------- Actor 更新 (策略梯度 + 熵奖励) --------
        prev_probs, prev_actor_hidden, _ = self._forward_actor(self.prev_state)
        # 策略梯度: ∇log π(a|s) * advantage
        # 对于交叉熵风格的离散动作: -advantage * (1 - prob[a]) for selected action
        prev_actor_hidden_raw = _vec_add(
            _mat_vec_mul(self.actor_w1, self.prev_state), self.actor_b1
        )

        # actor_w2 梯度
        actor_w2_grad = _zeros_mat(self.cfg.action_dim, self.cfg.hidden_dim)
        actor_b2_grad = _zeros_vec(self.cfg.action_dim)
        for a in range(self.cfg.action_dim):
            grad_factor = advantage
            if a == self.prev_action_idx:
                # 对于选中的动作: 梯度 = advantage * (1 - prob[a])
                grad_factor *= (1.0 - prev_probs[a])
            else:
                # 对于未选中的动作: 梯度 = -advantage * prob[a]
                grad_factor *= -prev_probs[a]
            # 加上熵正则化项
            if prev_probs[a] > 1e-12:
                grad_factor -= self.cfg.entropy_coef * (math.log(prev_probs[a]) + 1.0)

            for h in range(self.cfg.hidden_dim):
                self.actor_w2[a][h] -= self.cfg.actor_lr * grad_factor * prev_actor_hidden[h]
            self.actor_b2[a] -= self.cfg.actor_lr * grad_factor

        # actor_w1 和 b1 梯度 (relu 反向传播)
        factor_sum = [0.0] * self.cfg.hidden_dim
        for a in range(self.cfg.action_dim):
            grad_factor = advantage
            if a == self.prev_action_idx:
                grad_factor *= (1.0 - prev_probs[a])
            else:
                grad_factor *= -prev_probs[a]
            if prev_probs[a] > 1e-12:
                grad_factor -= self.cfg.entropy_coef * (math.log(prev_probs[a]) + 1.0)
            for h in range(self.cfg.hidden_dim):
                factor_sum[h] += grad_factor * self.actor_w2[a][h]

        for i in range(self.cfg.hidden_dim):
            if prev_actor_hidden_raw[i] > 0:
                for j in range(self.cfg.state_dim):
                    self.actor_w1[i][j] -= self.cfg.actor_lr * factor_sum[i] * self.prev_state[j]
                self.actor_b1[i] -= self.cfg.actor_lr * factor_sum[i]

        # 计算 actor loss（负对数概率 × advantage + 熵惩罚）
        selected_prob = max(prev_probs[self.prev_action_idx], 1e-12)
        actor_loss = -math.log(selected_prob) * advantage - self.cfg.entropy_coef * self.last_policy_entropy

        # -------- 状态更新 --------
        probs_new, _, entropy_new = self._forward_actor(current_state)
        critic_val_new, _ = self._forward_critic(current_state)
        self.prev_state = current_state
        self.prev_action_idx = current_action_idx
        self.prev_critic_value = critic_val_new
        self.last_policy_entropy = entropy_new
        self.last_td_error = td_error
        self.last_advantage = advantage
        self.episode_count += 1
        self.total_steps += 1

        # -------- 定期保存检查点 --------
        if self.episode_count % 20 == 0:
            self.save()

        return {
            "step": self.episode_count,
            "td_error": round(td_error, 6),
            "advantage": round(advantage, 6),
            "actor_loss": round(actor_loss, 6),
            "critic_loss": round(critic_loss, 6),
            "entropy": round(entropy_new, 6),
            "critic_value": round(critic_val_new, 6),
        }

    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------

    def save(self) -> str:
        """保存检查点到 JSON 文件。"""
        checkpoint = {
            "version": "a2c-trainer-1.0.0",
            "episode_count": self.episode_count,
            "total_steps": self.total_steps,
            "last_td_error": self.last_td_error,
            "last_advantage": self.last_advantage,
            "last_policy_entropy": self.last_policy_entropy,
            "actor_w1": [[round(w, 8) for w in row] for row in self.actor_w1],
            "actor_b1": [round(b, 8) for b in self.actor_b1],
            "actor_w2": [[round(w, 8) for w in row] for row in self.actor_w2],
            "actor_b2": [round(b, 8) for b in self.actor_b2],
            "critic_w1": [[round(w, 8) for w in row] for row in self.critic_w1],
            "critic_b1": [round(b, 8) for b in self.critic_b1],
            "critic_w2": [[round(w, 8) for w in row] for row in self.critic_w2],
            "critic_b2": [round(b, 8) for b in self.critic_b2],
            "config": self.cfg.to_dict(),
            "saved_at": int(time.time()),
        }
        path = Path(self.cfg.checkpoint_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(checkpoint, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(path)

    def _try_load(self) -> bool:
        """尝试从检查点恢复。"""
        path = Path(self.cfg.checkpoint_path)
        if not path.exists():
            return False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("version", "").startswith("a2c-trainer-"):
                self.episode_count = int(data.get("episode_count", 0))
                self.total_steps = int(data.get("total_steps", 0))
                self.last_td_error = float(data.get("last_td_error", 0.0))
                self.last_advantage = float(data.get("last_advantage", 0.0))
                self.last_policy_entropy = float(data.get("last_policy_entropy", 0.0))

                def _load_mat(key: str, rows: int, cols: int) -> list[list[float]]:
                    raw = data.get(key, [])
                    if raw and len(raw) == rows and all(len(r) == cols for r in raw):
                        return [[float(v) for v in row] for row in raw]
                    return _init_weights(rows, cols)

                self.actor_w1 = _load_mat("actor_w1", self.cfg.hidden_dim, self.cfg.state_dim)
                self.actor_b1 = [float(b) for b in data.get("actor_b1", _zeros_vec(self.cfg.hidden_dim))]
                self.actor_w2 = _load_mat("actor_w2", self.cfg.action_dim, self.cfg.hidden_dim)
                self.actor_b2 = [float(b) for b in data.get("actor_b2", _zeros_vec(self.cfg.action_dim))]
                self.critic_w1 = _load_mat("critic_w1", self.cfg.hidden_dim, self.cfg.state_dim)
                self.critic_b1 = [float(b) for b in data.get("critic_b1", _zeros_vec(self.cfg.hidden_dim))]
                self.critic_w2 = _load_mat("critic_w2", 1, self.cfg.hidden_dim)
                self.critic_b2 = [float(b) for b in data.get("critic_b2", [0.0])]
                return True
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            pass
        return False

    def reset(self) -> None:
        """重置训练器到初始状态。"""
        self.__init__(self.cfg, str(Path(self.cfg.checkpoint_path).parent))


# ------------------------------------------------------------------
# 全局单例入口（供 selector.py 和信号路由共用）
# ------------------------------------------------------------------

_DEFAULT_TRAINER: A2CTrainer | None = None


def get_a2c_trainer(checkpoint_dir: str = "data") -> A2CTrainer:
    """获取或创建全局 A2C 训练器单例。"""
    global _DEFAULT_TRAINER
    if _DEFAULT_TRAINER is None:
        _DEFAULT_TRAINER = A2CTrainer(checkpoint_dir=checkpoint_dir)
    return _DEFAULT_TRAINER


def reset_a2c_trainer() -> None:
    """重置全局单例（测试用）。"""
    global _DEFAULT_TRAINER
    if _DEFAULT_TRAINER is not None:
        _DEFAULT_TRAINER.reset()
    _DEFAULT_TRAINER = None