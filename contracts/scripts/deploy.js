const fs = require("fs");
const hre = require("hardhat");
const path = require("path");

function requireEnv(name) {
  const value = process.env[name];
  if (!value || value.trim() === "") {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

async function deployContract(name, args = []) {
  const Factory = await hre.ethers.getContractFactory(name);
  const contract = await Factory.deploy(...args);
  await contract.waitForDeployment();
  const address = await contract.getAddress();
  console.log(`${name} deployed to: ${address}`);
  return { contract, address };
}

function exportArtifact(contractName, address) {
  const artifactPath = path.join(
    __dirname,
    "..",
    "artifacts",
    "contracts",
    `${contractName}.sol`,
    `${contractName}.json`,
  );
  const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));
  const exportPath = path.join(__dirname, "..", "artifacts", `${contractName}.json`);
  fs.mkdirSync(path.dirname(exportPath), { recursive: true });
  fs.writeFileSync(
    exportPath,
    JSON.stringify({ address, abi: artifact.abi, network: hre.network.name }, null, 2),
    "utf8",
  );
}

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  if (!deployer) {
    throw new Error("No deployer signer configured. Set MANTLE_PRIVATE_KEY in contracts/.env.");
  }

  console.log(`Deploying with ${deployer.address} on ${hre.network.name}`);
  const signal = await deployContract("SignalRegistry");
  const card = await deployContract("ERC8004AgentCard");

  const reclaimAddress =
    process.env.RECLAIM_VERIFIER_ADDRESS || process.env.RECLAIM_ADDRESS || "";
  let executor = null;
  if (reclaimAddress) {
    executor = await deployContract("QuantAgentExecutor", [reclaimAddress, signal.address]);
  } else {
    console.log("Skipping QuantAgentExecutor deployment: RECLAIM_VERIFIER_ADDRESS not configured.");
  }

  exportArtifact("SignalRegistry", signal.address);
  exportArtifact("ERC8004AgentCard", card.address);
  if (executor) exportArtifact("QuantAgentExecutor", executor.address);

  const deployment = {
    network: hre.network.name,
    chainId: Number((await hre.ethers.provider.getNetwork()).chainId),
    deployer: deployer.address,
    SignalRegistry: signal.address,
    ERC8004AgentCard: card.address,
    QuantAgentExecutor: executor ? executor.address : null,
    ReclaimVerifier: reclaimAddress || null,
    deployedAt: new Date().toISOString(),
  };
  const deploymentPath = path.join(__dirname, "..", "artifacts", `deployment-${hre.network.name}.json`);
  fs.writeFileSync(deploymentPath, JSON.stringify(deployment, null, 2), "utf8");
  console.log(`Deployment manifest: ${deploymentPath}`);
  console.log(JSON.stringify(deployment, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
