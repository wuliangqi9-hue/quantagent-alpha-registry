const fs = require("fs");
const hre = require("hardhat");
const path = require("path");

async function main() {
  const SignalRegistry = await hre.ethers.getContractFactory("SignalRegistry");
  const registry = await SignalRegistry.deploy();
  await registry.waitForDeployment();
  const address = await registry.getAddress();
  console.log("SignalRegistry deployed to:", address);

  const artifactPath = path.join(__dirname, "..", "artifacts", "contracts", "SignalRegistry.sol", "SignalRegistry.json");
  const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));
  const exportPath = path.join(__dirname, "..", "artifacts", "SignalRegistry.json");
  fs.mkdirSync(path.dirname(exportPath), { recursive: true });
  fs.writeFileSync(
    exportPath,
    JSON.stringify({ address, abi: artifact.abi }, null, 2),
    "utf8"
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
