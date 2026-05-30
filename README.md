---
title: QuantAgent Demo
emoji: 🤖
colorFrom: blue
colorTo: gray
sdk: docker
pinned: false
---

# 🤖 QuantAgent Alpha Registry

> **全球首个基于 ERC-8004、TEE 与 ZK-TLS 构建的可信链上 AI 量化交易代理网络。**
>
> *本项目为 DoraHacks 黑客松参赛作品，深度集成 Mantle Network。*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Node.js](https://img.shields.io/badge/Node.js-18.x-green.svg)](https://nodejs.org/)
[![Smart Contracts](https://img.shields.io/badge/Contracts-Solidity_0.8.20-363636.svg)](https://soliditylang.org/)

## 🌟 项目愿景 (Overview)

传统的加密货币量化交易面临两大痛点：**策略黑盒化（缺乏信任）**与**策略资产化困难（缺乏流动性）**。

**QuantAgent Alpha Registry** 致力于打破这一现状。我们通过独创的架构，将复杂的 AI 强化学习量化模型与 Web3 智能合约完美融合：

- 利用 **ERC-8004** 标准，我们将 AI Agent 本身及其交易策略封装为可验证、可交易的链上资产。
- 引入 **TEE（可信执行环境）** 与 **ZK-TLS（零知识传输层安全 / Reclaim 协议）**，在不暴露核心策略代码的前提下，向链上密码学层面证明“交易信号确实是由真实的链下市场数据生成的”。

## 🔥 核心创新点与技术基石 (Core Innovations & Technical Foundations)

本项目的底层架构不仅是工程上的拼图，更是对当前密码学、强化学习与去中心化金融前沿研究的直接应用。

### 1. 零知识传输层安全与数据溯源 (ZK-TLS & Data Provenance)

在量化交易中，数据的真实性决定了策略的有效性。传统预言机存在中心化作恶风险，我们通过集成 **ZK-TLS (Zero-Knowledge Transport Layer Security)** 技术解决了这一痛点。

- **具体技术**: 利用 Reclaim Protocol 及底层的多方安全计算 (MPC) 技术。Agent 在与中心化交易所 (CEX) 或 Web2 数据源建立 TLS 1.3 连接时，能在不暴露 API Key 的情况下，生成关于“特定数据确实来源于特定 HTTPS 响应”的 ZK-SNARK 证明，并提交至 `SignalRegistry.sol` 验证。
- **学术渊源**: 基础理论源于 ACM CCS 2020 顶会论文 *DECO: Liberating Web Data Using Decentralized Oracles for TLS* (Zhang et al.)。该论文首次提出了在不修改现有 TLS 协议前提下，对 Web 数据进行零知识证明的范式。

### 2. TEE 隔离边界内的去信任推理 (Trustless Inference via TEE)

即便数据来源可信，如何证明 AI 模型的推理过程未被篡改？我们将整个 Agent 核心逻辑部署于 **TEE (可信执行环境)** 内。

- **具体技术**: 利用硬件级内存隔离 (如 Intel SGX 或 AWS Nitro Enclaves)。Agent 在 TEE 内接收 ZK-TLS 验证过的数据，运行量化模型，并最终使用封装在 enclave 内的私钥对交易决策 (Decision Summary) 进行签名 (ECDSA)。
- **学术渊源**: 架构灵感参考自 IEEE S&P 经典论文 *Town Crier: An Authenticated Data Feed for Smart Contracts* (Zhang et al., 2016)，将 SGX 硬件级信任引入智能合约。

### 3. 极简强化学习与动态机制路由 (Regime-Aware A2C Reinforcement Learning)

加密货币市场处于极端的非平稳状态 (Non-stationary)，静态规则极易失效。我们摒弃了臃肿的深度学习框架，实现了一套极简、无依赖的在线强化学习路由。

- **具体技术**: 在 `packages/strategy-selector` 中，基于纯 NumPy 构建了 **A2C (Advantage Actor-Critic)** 模型。Actor 网络负责输出在不同市场机制 (Regime Strategy) 下的策略融合权重 (Policy Blending)，Critic 网络评估当前头寸状态 (FinPos) 的价值。同时引入了熵正则化 (Entropy Regularization) 以鼓励在极端行情中的探索，避免陷入局部最优。
- **学术渊源**: 算法内核基于 DeepMind 的奠基性论文 *Asynchronous Methods for Deep Reinforcement Learning* (Mnih et al., ICML 2016)。金融应用参考了 *Deep Reinforcement Learning for Algorithmic Trading* 系列文献，将离散动作空间映射为连续的资金配置比例。

### 4. ERC-8004：自治代理的资产化范式 (Tokenization of Autonomous Agents)

我们将上述复杂的 AI 推理与密码学证明，统一封装进智能合约接口中，赋予 AI 独立经济实体的属性。

- **具体技术**: 深度定制了 `ERC8004AgentCard.sol`。有别于传统的 ERC-721 仅记录静态元数据，我们将 Agent 的策略描述、API 回调端点、订阅收费模型以及历史声誉值 (Reputation) 结构化上链。结合 Mantle 网络的低延迟特性，实现了高频量化信号的去中心化分发与结算。
- **学术渊源**: 探索了去中心化自治代理 (Decentralized Autonomous Agents, DAAs) 的前沿概念，将金融衍生品的可组合性 (Composability) 扩展到了 AI 模型层面。

## 🏗️ 系统架构 (Architecture)

本项目采用现代化的全栈 Monorepo 工程结构，确保算法引擎、后端服务与前端 dApp 的无缝协同：

```text
quantagent-alpha-registry/
├── apps/                   # 终端应用
│   └── web/                # React + Vite 前端 (Agent Terminal, Proof Panel)
├── contracts/              # 智能合约 (Hardhat)
│   └── contracts/          # ERC8004AgentCard.sol, SignalRegistry.sol, QuantAgentExecutor.sol
├── packages/               # 核心算法与引擎库
│   ├── agent-memory/       # LLM Agent 记忆与上下文管理
│   ├── agent-orchestrator/ # 多智能体任务编排系统
│   ├── factor-engine/      # 因子计算引擎 (多维度市场数据处理)
│   └── strategy-selector/  # A2C 强化学习与金融头寸管理模型
├── services/               # 后端 API 服务
│   └── api/                # FastAPI 服务 (TEE/ZK-TLS 验证, A2C 适配, 链上交互)
└── scripts/                # 自动化运维与启动脚本
```

## 🚀 快速开始 (Quick Start)

### 1. 环境准备 (Prerequisites)

- [Node.js](https://nodejs.org/) v18+ 与 `npm` / `pnpm`
- [Python](https://www.python.org/) 3.10+
- 推荐使用 Windows PowerShell 或类 Unix 终端运行脚本。

### 2. 克隆项目 & 环境变量

```bash
git clone https://github.com/wuliangqi9-hue/quantagent-alpha-registry.git
cd quantagent-alpha-registry

# 配置根目录与合约目录环境变量
cp .env.example .env
cp contracts/.env.example contracts/.env
```

请在 `.env` 文件中填入您的 LLM API Keys、RPC 节点、Mantle 私钥与合约地址信息。

### 3. 一键启动服务 (Start Services)

项目提供了便捷的自动化脚本。

**启动后端 API (FastAPI & AI 引擎):**

```powershell
./scripts/run_api.ps1
```

API 服务将在 `http://localhost:8000` 启动，并自动加载因子引擎与策略选择器。

**启动前端 dApp (React 终端):**

```powershell
./scripts/run_web.ps1
```

Web 应用将在 `http://localhost:5173` 启动。您可以在看板中查看 Agent Passport、执行状态面板与 ZK-TLS 证明。

### 4. 智能合约部署 (Contract Deployment)

```bash
cd contracts
npm install
npx hardhat compile
npx hardhat run scripts/deploy.js --network mantleSepolia
```

## 🛡️ 安全与证明模型 (Proof Model)

为了保障系统的去中心化安全，我们在链下生成交易决策后，必须通过以下管道：

1. **数据抓取**: 核心因子数据通过 ZK-TLS 建立安全信道抓取。
2. **TEE 推理**: A2C 模型在可信环境中运行，并生成带签名的交易意图（Decision Summary）。
3. **链上验证**: `SignalRegistry.sol` 会校验决策的签名与 ZK Proof，验证通过后方可由 `QuantAgentExecutor.sol` 触发链上代币交易。

更多技术细节请参阅 [docs/proof-model.md](./docs/proof-model.md)。

## 🤝 贡献与评审 (Judging & Contribution)

对于 DoraHacks 评审委员，请参考以下文档快速了解本项目的完整逻辑：

- [产品演示脚本 (Demo Script)](./docs/demo-script.md)
- [架构深度解析 (Architecture)](./docs/architecture.md)
- [评审对照清单 (Judging Checklist)](./docs/judging-checklist.md)

## ⚠️ 免责声明 (Disclaimer)

本项目包含复杂的实验性金融算法和智能合约。代码及策略仅用于黑客松演示与学术交流目的，**不构成任何投资或财务建议**。加密资产具有极高的风险，在主网部署和投入真实资金前，请务必进行全面的代码审计。
