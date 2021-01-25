require('dotenv').config();
const ethers = require('ethers');
const util = require('./util');
const MockContract = require('../artifacts/contracts/MockContract.sol/MockContract.json');

const TIME_BETWEEN_TXES_IN_MINUTES = 1; // Set this large enough

const TEST_CASES = {
  recommended: true,
  rand1: true,
  hybrid: true,
  boosted10: true // recommended + 10%
};

async function main() {
  const provider = new ethers.providers.JsonRpcProvider(process.env.PROVIDER_URL);
  const wallets = [
    ethers.Wallet.fromMnemonic(process.env.MNEMONIC_1).connect(provider),
    ethers.Wallet.fromMnemonic(process.env.MNEMONIC_2).connect(provider),
    ethers.Wallet.fromMnemonic(process.env.MNEMONIC_3).connect(provider),
    ethers.Wallet.fromMnemonic(process.env.MNEMONIC_4).connect(provider)
  ];

  const mockContract = new ethers.Contract(
    util.readFromLogJson('mockContractAddress'),
    MockContract.abi
  );

  const testCases = [];
  for (const testCase in TEST_CASES) {
    if (TEST_CASES[testCase]) {
      testCases.push(testCase);
    }
  }

  let txNo = 1;
  setInterval(async () => {
    console.log(`tx #${txNo}`);
    // Sample gas price from the current block
    const submitBlockNumber = await provider.getBlockNumber();
    const submitBlock = await provider.getBlock(submitBlockNumber);
    // Skip this block if empty
    if (submitBlock.transactions.length == 0) {
      return;
    }
    txNo++;
    const sampledTxHash = submitBlock.transactions[Math.floor(Math.random() * submitBlock.transactions.length)];
    const sampledTx = await provider.getTransaction(sampledTxHash);
    const sampleGasPrice = sampledTx.gasPrice;

    // Get the recommended gas price
    const recommendedGasPrice = await provider.getGasPrice();

    // Treat each test case separately, but in parallel
    testCases.forEach(async (testCase, indTestCase) => {
      let usedGasPrice;
      if (testCase == 'recommended') {
        usedGasPrice = recommendedGasPrice;
      }
      else if (testCase == 'rand1') {
        usedGasPrice = sampleGasPrice;
      }
      else if (testCase == 'hybrid') {
        if (sampleGasPrice.gt(recommendedGasPrice.mul(2))) {
          usedGasPrice = recommendedGasPrice.mul(2);
        }
        else if (sampleGasPrice.lt(recommendedGasPrice)) {
          usedGasPrice = recommendedGasPrice;
        }
        else {
          usedGasPrice = sampleGasPrice;
        }
      }
      else if (testCase == 'boosted10') {
        usedGasPrice = recommendedGasPrice.mul(11).div(10);
      }

      // Make the transaction
      const receipt = await mockContract
        .connect(wallets[indTestCase])
        .updateData(
          Math.round(Math.random() * 1000),
          { gasPrice: usedGasPrice }
          );
      // Wait until it's confirmed
      await receipt.wait();
      // Find out when it was confirmed
      const tx = await provider.getTransaction(receipt.hash);

      util.addTx(testCase, {
        submitBlockNumber,
        confirmBlockNumber: tx.blockNumber,
        sampleGasPrice: sampleGasPrice.toString(),
        recommendedGasPrice: recommendedGasPrice.toString(),
        usedGasPrice: usedGasPrice.toString(),
        hash: receipt.hash
      });
    });
  }, TIME_BETWEEN_TXES_IN_MINUTES * 60 * 1000);
}

main();
