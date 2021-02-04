const fs = require('fs');

function readLogJson(filePath) {
  if (fs.existsSync(filePath)) {
    return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
  }
  return {};
}

// https://stackoverflow.com/questions/2450954/how-to-randomize-shuffle-a-javascript-array
function shuffle(array) {
  var currentIndex = array.length, temporaryValue, randomIndex;

  // While there remain elements to shuffle...
  while (0 !== currentIndex) {

    // Pick a remaining element...
    randomIndex = Math.floor(Math.random() * currentIndex);
    currentIndex -= 1;

    // And swap it with the current element.
    temporaryValue = array[currentIndex];
    array[currentIndex] = array[randomIndex];
    array[randomIndex] = temporaryValue;
  }

  return array;
}

module.exports = {
  updateLogJson: function (name, value) {
    const filePath = './log.json';
    const logJson = readLogJson(filePath);
    logJson[name] = value;
    fs.writeFileSync(filePath, JSON.stringify(logJson, null, 4));
  },
  readFromLogJson: function (name) {
    const filePath = './log.json';
    return readLogJson(filePath)[name];
  },
  addTx: function (testCase, entry) {
    let txes = [];
    const filePath = `./txes_${testCase}.json`;
    if (fs.existsSync(filePath)) {
      txes = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
    }
    txes.push(entry);
    fs.writeFileSync(filePath, JSON.stringify(txes, null, 4));
  },
  sleep: function (ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  },
  shuffle: function (array) {
    return shuffle(array);
  },
};

