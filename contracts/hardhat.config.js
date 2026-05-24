require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config({ path: require("path").join(__dirname, ".env") });

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: {
    compilers: [
      {
        version: "0.8.20",
        settings: {
          optimizer: {
            enabled: true,
            runs: 200,
          },
          viaIR: true,
        },
      },
      {
        version: "0.8.4",
        settings: {
          optimizer: {
            enabled: true,
            runs: 200,
          },
          viaIR: true,
        },
      },
    ],
  },
  paths: {
    sources: "./contracts",
    artifacts: "./artifacts",
  },
  networks: {
    mantleSepolia: {
      url: process.env.MANTLE_RPC_URL || "https://rpc.sepolia.mantle.xyz",
      chainId: Number(process.env.MANTLE_CHAIN_ID || 5003),
      accounts: process.env.MANTLE_PRIVATE_KEY ? [process.env.MANTLE_PRIVATE_KEY] : [],
    },
    mantleMainnet: {
      url: process.env.MANTLE_MAINNET_RPC_URL || "https://rpc.mantle.xyz",
      chainId: 5000,
      accounts: process.env.MANTLE_MAINNET_PRIVATE_KEY
        ? [process.env.MANTLE_MAINNET_PRIVATE_KEY]
        : process.env.MANTLE_PRIVATE_KEY
          ? [process.env.MANTLE_PRIVATE_KEY]
          : [],
    },
    byrealTestnet: {
      url: process.env.BYREAL_RPC_URL || "https://rpc-testnet.byreal.io",
      chainId: Number(process.env.BYREAL_CHAIN_ID || 6868),
      accounts: process.env.BYREAL_PRIVATE_KEY
        ? [process.env.BYREAL_PRIVATE_KEY]
        : process.env.MANTLE_PRIVATE_KEY
          ? [process.env.MANTLE_PRIVATE_KEY]
          : [],
    },
  },
};
