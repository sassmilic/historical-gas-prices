require('dotenv').config();
const ethers = require('ethers');
const util = require('./util');
const MockContract = require('../artifacts/contracts/MockContract.sol/MockContract.json');

async function main() {
  const provider = new ethers.providers.JsonRpcProvider(process.env.PROVIDER_URL);
  const wallet = (ethers.Wallet.fromMnemonic(process.env.MNEMONIC)).connect(provider);

  const MockContractFactory = new ethers.ContractFactory(
    MockContract.abi,
    MockContract.bytecode,
    wallet
  );
  const mockContract = await MockContractFactory.deploy();
  util.updateLogJson('mockContractAddress', mockContract.address);
  console.log(`Mock contract address: ${mockContract.address}`);
}

main();
