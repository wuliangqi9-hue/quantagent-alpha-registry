const { expect } = require("chai");
const { ethers } = require("hardhat");

function agentInfo(owner) {
  return {
    name: "QuantAgent Alpha",
    description: "AI Trading Bot",
    version: "1.0.0",
    agentType: "quant-trading",
    capabilities: ["factor-analysis"],
    apiEndpoints: ["https://example.com/analyze", "https://example.com/settle"],
    trustModel: "tee-zktls-reputation",
    paymentWallet: owner.address,
    termsURI: "ipfs://terms",
    iconURI: "ipfs://icon",
  };
}

function agentMeta() {
  return {
    supportedChains: ["eip155:5003"],
    supportedAssets: ["BTC", "ETH", "SOL"],
    strategyCategories: ["trend-following"],
    minExecutionSize: 0,
    maxExecutionSize: 0,
    feeBps: 0,
    feeModel: "none",
    complianceInfo: "demo",
  };
}

function proofFor(agentId, signalHash, extraHashes = []) {
  const boundHashes = extraHashes.map((hash) => `"${hash}"`).join(",");
  return {
    claimInfo: {
      provider: "reclaim",
      parameters: `{"agentId":${agentId},"signalHash":"${signalHash}","boundHashes":[${boundHashes}]}`,
      context: "quantagent execution proof",
    },
    signedClaim: {
      claim: {
        identifier: ethers.ZeroHash,
        owner: ethers.ZeroAddress,
        timestampS: 0,
        epoch: 0,
      },
      signatures: [],
    },
  };
}

describe("Registry hardening", function () {
  it("updates API endpoints without retaining stale entries and caps custom property size", async function () {
    const [owner] = await ethers.getSigners();
    const Card = await ethers.getContractFactory("ERC8004AgentCard");
    const card = await Card.deploy();
    await card.waitForDeployment();

    await card.register(1, agentInfo(owner), agentMeta());
    await card.updateApiEndpoints(1, ["https://example.com/only"]);

    const info = await card.getAgentCardInfo(1);
    expect(info.apiEndpoints).to.deep.equal(["https://example.com/only"]);

    await expect(card.setCustomProperty(1, "k".repeat(65), "value")).to.be.revertedWith(
      "ERC8004AgentCard: key too long",
    );
    await expect(card.setCustomProperty(1, "key", "v".repeat(513))).to.be.revertedWith(
      "ERC8004AgentCard: value too long",
    );
  });

  it("preserves an independent agent wallet during NFT transfer", async function () {
    const [owner, agentWallet, buyer] = await ethers.getSigners();
    const Registry = await ethers.getContractFactory("SignalRegistry");
    const registry = await Registry.deploy();
    await registry.waitForDeployment();

    await registry.registerWithWallet("https://example.com/card.json", agentWallet.address);
    await registry.transferFrom(owner.address, buyer.address, 1);

    expect(await registry.getAgentWallet(1)).to.equal(agentWallet.address);
  });

  it("binds Reclaim proof data to signal payload before recording", async function () {
    const [owner] = await ethers.getSigners();
    const Registry = await ethers.getContractFactory("SignalRegistry");
    const registry = await Registry.deploy();
    await registry.waitForDeployment();
    await registry.register("https://example.com/card.json");

    const Reclaim = await ethers.getContractFactory("MockReclaimVerifier");
    const reclaim = await Reclaim.deploy();
    await reclaim.waitForDeployment();

    const Executor = await ethers.getContractFactory("QuantAgentExecutor");
    const executor = await Executor.deploy(await reclaim.getAddress(), await registry.getAddress());
    await executor.waitForDeployment();
    await registry.setAgentWallet(1, await executor.getAddress());

    const signalHash = ethers.keccak256(ethers.toUtf8Bytes("signal"));
    const payload = {
      agentId: 1,
      signalHash,
      assetSymbol: "BTC",
      strategyId: "supertrend",
      modelVersion: "test",
      mode: "test",
      proofURI: "ipfs://proof",
      proofHash: ethers.keccak256(ethers.toUtf8Bytes("proof")),
    };

    await expect(executor.executeTradeWithProof(proofFor(2, signalHash), payload)).to.be.revertedWith(
      "proof/payload mismatch",
    );
    await expect(executor.executeTradeWithProof(proofFor(1, signalHash), payload)).to.emit(
      executor,
      "TradeProofVerified",
    );
  });

  it("rejects duplicate signal hashes and non-controller signal writers", async function () {
    const [owner, agentWallet, attacker] = await ethers.getSigners();
    const Registry = await ethers.getContractFactory("SignalRegistry");
    const registry = await Registry.deploy();
    await registry.waitForDeployment();
    await registry.registerWithWallet("https://example.com/card.json", agentWallet.address);

    const signalHash = ethers.keccak256(ethers.toUtf8Bytes("unique signal"));
    const proofHash = ethers.keccak256(ethers.toUtf8Bytes("proof"));

    await expect(
      registry.connect(attacker).recordSignalForAgent(
        1,
        signalHash,
        "BTC",
        "supertrend",
        "test",
        "test",
        owner.address,
        "ipfs://proof",
        proofHash,
      ),
    ).to.be.revertedWith("not agent controller");

    await expect(
      registry.connect(agentWallet).recordSignalForAgent(
        1,
        signalHash,
        "BTC",
        "supertrend",
        "test",
        "test",
        owner.address,
        "ipfs://proof",
        proofHash,
      ),
    ).to.emit(registry, "SignalRecorded");

    await expect(
      registry.connect(agentWallet).recordSignalForAgent(
        1,
        signalHash,
        "BTC",
        "supertrend",
        "test",
        "test",
        owner.address,
        "ipfs://proof",
        proofHash,
      ),
    ).to.be.revertedWith("already recorded");
  });

  it("rejects reputation feedback from non-controller accounts", async function () {
    const [owner, attacker] = await ethers.getSigners();
    const Registry = await ethers.getContractFactory("SignalRegistry");
    const registry = await Registry.deploy();
    await registry.waitForDeployment();
    await registry.register("https://example.com/card.json");

    await expect(
      registry.connect(attacker).giveFeedback(
        1,
        100,
        2,
        "pnl-bps",
        "long",
        "quantagent-alpha-registry",
        "ipfs://feedback",
        ethers.keccak256(ethers.toUtf8Bytes("feedback")),
      ),
    ).to.be.revertedWith("not agent controller");

    await expect(
      registry.giveFeedback(
        1,
        100,
        2,
        "pnl-bps",
        "long",
        "quantagent-alpha-registry",
        "ipfs://feedback",
        ethers.keccak256(ethers.toUtf8Bytes("feedback")),
      ),
    ).to.emit(registry, "NewFeedback");

    const summary = await registry.getReputationSummary(1);
    expect(summary.count).to.equal(1n);
    expect(summary.summaryValue).to.equal(100n);
    expect(summary.summaryValueDecimals).to.equal(2n);
  });

  it("can settle a token transfer behind the proof gate", async function () {
    const [owner, recipient] = await ethers.getSigners();
    const Registry = await ethers.getContractFactory("SignalRegistry");
    const registry = await Registry.deploy();
    await registry.waitForDeployment();
    await registry.register("https://example.com/card.json");

    const Reclaim = await ethers.getContractFactory("MockReclaimVerifier");
    const reclaim = await Reclaim.deploy();
    await reclaim.waitForDeployment();

    const Executor = await ethers.getContractFactory("QuantAgentExecutor");
    const executor = await Executor.deploy(await reclaim.getAddress(), await registry.getAddress());
    await executor.waitForDeployment();
    await registry.setAgentWallet(1, await executor.getAddress());

    const Token = await ethers.getContractFactory("MockERC20");
    const token = await Token.deploy();
    await token.waitForDeployment();
    await token.mint(owner.address, 1000n);
    await token.approve(await executor.getAddress(), 100n);

    const signalHash = ethers.keccak256(ethers.toUtf8Bytes("settled-signal"));
    const payload = {
      agentId: 1,
      signalHash,
      assetSymbol: "ETH",
      strategyId: "bollinger",
      modelVersion: "test",
      mode: "test",
      proofURI: "ipfs://proof",
      proofHash: ethers.keccak256(ethers.toUtf8Bytes("proof")),
    };

    const settlement = {
      asset: await token.getAddress(),
      from: owner.address,
      to: recipient.address,
      amount: 100n,
      routeHash: ethers.ZeroHash,
    };
    settlement.routeHash = await executor.settlementIntentHash(settlement);

    await expect(
      executor.executeTradeWithProofAndSettlement(proofFor(1, signalHash), payload, {
        ...settlement,
        routeHash: ethers.keccak256(ethers.toUtf8Bytes("tampered route")),
      }),
    ).to.be.revertedWith("settlement route mismatch");

    await expect(
      executor.executeTradeWithProofAndSettlement(proofFor(1, signalHash), payload, settlement),
    ).to.be.revertedWith("settlement/proof mismatch");

    await expect(
      executor.executeTradeWithProofAndSettlement(proofFor(1, signalHash, [settlement.routeHash]), payload, settlement),
    ).to.emit(executor, "SettlementIntentExecuted");

    expect(await token.balanceOf(recipient.address)).to.equal(100n);
  });
});
