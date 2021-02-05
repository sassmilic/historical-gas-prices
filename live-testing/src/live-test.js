require('dotenv').config();
const ethers = require('ethers');
const util = require('./util');
const MockContract = require('../artifacts/contracts/MockContract.sol/MockContract.json');

const TIME_BETWEEN_TXES_IN_MINUTES = 1; // Set this large enough

const TEST_CASES = {
  recommended: true,
  //rand1: true,
  hybrid: true,
  boosted10: true // recommended + 10%
};

async function main() {
  console.log('Provider URL: %s', process.env.PROVIDER_URL);
  const provider = new ethers.providers.JsonRpcProvider(process.env.PROVIDER_URL);
  const mnemos = [
    process.env.MNEMONIC_1,
    process.env.MNEMONIC_2,
    process.env.MNEMONIC_3,
    //process.env.MNEMONIC_4
  ];

  const wallets = [];
  mnemos.forEach(function(x){
    wallets.push(ethers.Wallet.fromMnemonic(x).connect(provider))
  })

  for (const w of wallets) {
    let balance = await provider.getBalance(w.address);
    console.log("Using wallet address %s. Current balance: %d", w.address, balance);
  }

  const mockContract = new ethers.Contract(
    util.readFromLogJson('mockContractAddress'),
    MockContract.abi
  );

  let testCases = [];
  for (const testCase in TEST_CASES) {
    if (TEST_CASES[testCase]) {
      testCases.push(testCase);
    }
  }

  console.log('Entering loop ...');

  let txNo = 1;
  setInterval(async () => {
    console.log(`tx #${txNo}`);
    // Sample gas price from the current block
    const submitBlockNumber = await provider.getBlockNumber();
    const submitBlock = await provider.getBlock(submitBlockNumber);
    // Skip this block if empty
    if (submitBlock.transactions.length == 0) {
        console.log('Most recent block is empty.');
        return;
    }
    txNo++;

    let sampledTxHash = submitBlock.transactions[Math.floor(Math.random() * submitBlock.transactions.length)];
    let sampledTx = await provider.getTransaction(sampledTxHash);

    let timeout = 0;
    while (sampledTx == null) {
        console.log('Sample txn returned null. Retrying.');
        let sampledTxHash = submitBlock.transactions[Math.floor(Math.random() * submitBlock.transactions.length)];
        let sampledTx = await provider.getTransaction(sampledTxHash);
        util.sleep(500);
        timeout++;
        if (timeout == 10) {
            console.log('Timed out.');
            return;
        }
    }

    const sampleGasPrice = sampledTx.gasPrice;

    // Get the recommended gas price
    const recommendedGasPrice = await provider.getGasPrice();

    // Treat each test case separately, but in parallel.

    // Shuffle `testCases` each time to eliminate any chance
    // that ordering affects results.
    util.shuffle(testCases);
    console.log('Test case ordering: ', testCases);

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

      console.log(
        "Method:\t", testCase,
        ".\tUsed gas price: ", usedGasPrice.toString()
      );

      // Make the transaction
      let txnCreated = Date.now();

      // Set nonce manually because we want to override previous pending txns.
      // Most providers take into account pending txns when computing nonce.
      let txn_count = await provider.getTransactionCount(wallets[indTestCase].address);

      const receipt = await mockContract
        .connect(wallets[indTestCase])
        .updateData(
          Math.round(Math.random() * 1000),
          {
              gasPrice: usedGasPrice,
              gasLimit: 22000,
              nonce: txn_count
          }
        );

      // Wait a minute to check if confirmed
      await util.sleep(60 * 1000);

      const tx = await provider.getTransaction(receipt.hash);

      if (tx == null || tx.confirmations == 0) {
        console.log('Failed to confirm transaction %s', receipt.hash);
        util.addTx(testCase, {
          submitBlockNumber,
          createTimestamp: txnCreated,
          confirmBlockNumber: null,
          currentBlockTimestamp: submitBlock.timestamp,
          confirmTimestamp: null,
          sampleGasPrice: sampleGasPrice.toString(),
          recommendedGasPrice: recommendedGasPrice.toString(),
          usedGasPrice: usedGasPrice.toString(),
          hash: null
        });
        return;
      }

      console.log('Transaction %s confirmed with %d confirmations', receipt.hash, tx.confirmations);

      util.addTx(testCase, {
        submitBlockNumber,
        createTimestamp: txnCreated,
        confirmBlockNumber: tx.blockNumber,
        currentBlockTimestamp: submitBlock.timestamp,
        confirmTimestamp: (await provider.getBlock(tx.blockNumber)).timestamp,
        sampleGasPrice: sampleGasPrice.toString(),
        recommendedGasPrice: recommendedGasPrice.toString(),
        usedGasPrice: usedGasPrice.toString(),
        hash: receipt.hash
      });
    });
  }, TIME_BETWEEN_TXES_IN_MINUTES * 60 * 1000);
}

main();
