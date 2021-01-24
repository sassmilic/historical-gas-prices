require('dotenv').config();
const ethers = require('ethers');
const util = require('./util');
const MockContract = require('../artifacts/contracts/MockContract.sol/MockContract.json');

async function main() {
  const provider = new ethers.providers.JsonRpcProvider(process.env.PROVIDER_URL);
  const wallet = (ethers.Wallet.fromMnemonic(process.env.MNEMONIC)).connect(provider);

  const mockContract = new ethers.Contract(
    util.readFromLogJson('mockContractAddress'),
    MockContract.abi,
    wallet
  );

  let data = 1;
  setInterval(async () => {
    console.log(`tx #${data}`);
    // Sample gas price from the current block
    const submitBlockNumber = await provider.getBlockNumber();
    const submitBlock = await provider.getBlock(submitBlockNumber);
    // Skip this block if empty
    if (submitBlock.transactions.length == 0) {
      return;
    }
    const sampledTxHash = submitBlock.transactions[Math.floor(Math.random() * submitBlock.transactions.length)];
    const sampledTx = await provider.getTransaction(sampledTxHash);
    const sampleGasPrice = sampledTx.gasPrice;

    // Get the recommended gas price
    const recommendedGasPrice = await provider.getGasPrice();
    
    // Calculate the gas price to be used
    let usedGasPrice;
    if (sampleGasPrice.gt(recommendedGasPrice.mul(2))) {
      usedGasPrice = recommendedGasPrice.mul(2);
    }
    else if (sampleGasPrice.lt(recommendedGasPrice)) {
      usedGasPrice = recommendedGasPrice;
    }
    else {
      usedGasPrice = sampleGasPrice;
    }

    // Make the transaction
    const receipt = await mockContract.updateData(data++);
    // Wait until it's confirmed
    await receipt.wait();
    // Find out when it was confirmed
    const tx = await provider.getTransaction(receipt.hash);

    util.addTx({
      submitBlockNumber,
      confirmBlockNumber: tx.blockNumber,
      sampleGasPrice: sampleGasPrice.toString(),
      recommendedGasPrice: recommendedGasPrice.toString(),
      usedGasPrice: usedGasPrice.toString(),
      hash: receipt.hash
    });  
  }, 60 * 1000); // Every minute
}

main();
