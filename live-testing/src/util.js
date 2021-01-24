const fs = require('fs');

function readLogJson(filePath) {
  if (fs.existsSync(filePath)) {
    return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
  }
  return {};
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
  addTx: function (entry) {
    let txes = [];
    const filePath = './txes.json';
    if (fs.existsSync(filePath)) {
      txes = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
    }
    txes.push(entry);
    fs.writeFileSync(filePath, JSON.stringify(txes, null, 4));
  },
};
