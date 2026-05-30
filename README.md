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

## 🔥 核心创新点 (Key Innovations)

- 🪪 **ERC-8004 策略资产化 (Agent Tokenization)**: 将抽象的量化策略实体化为链上卡片 (Agent Card)，实现策略的订阅、分发与可组合性。
- 🔒 **零知识可信计算 (Verifiable Execution)**: 结合 `TEE` 与 `ZK-TLS`，确保链下 API 数据的真实性以及 AI 推理过程未被篡改，实现真正的 Trustless 交易信号注册。
- 🧠 **深度强化学习路由 (A2C Strategy Selector)**: 摒弃静态规则，采用 Advantage Actor-Critic (A2C) 模型。AI 根据当前极端的加密市场机制 (Regime Strategy) 动态进行多策略融合 (Policy Blending) 与头寸管理。
- 📊 **高维全景因子引擎 (Factor Engine)**: 实时处理衍生品 (Derivatives)、市场深度 (Market) 和 Mantle 原生链上数据 (On-chain)，为 AI 提供军工级的数据弹药。

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
