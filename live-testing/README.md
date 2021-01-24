# Tool to live-test Airnode gas price strategy

## Instructions

1. `npm install`
1. `npm run build`
1. Create a `.env` file similar to the [example.env](/live-testing/example.env) file
1. `npm run deploy`
1. `npm run live-test` will calculate the has price and make a transaction with it every minute

New transactions will be recorded in `txes.json`.
`Ctrl-C` when you've had enough.

## Example output at `txes.json` on Ropsten

The 3–4 calls made between `submitBlockNumber` and the actual submission probably adds around a 1 second delay.

```json
[
    {
        "submitBlockNumber": 9527483,
        "confirmBlockNumber": 9527485,
        "sampleGasPrice": "4900620208",
        "recommendedGasPrice": "4900620208",
        "usedGasPrice": "4900620208",
        "hash": "0xf9402c90c4ee4884513f2142f210778cf157c71f2056f4ee2914c3273c85f6ce"
    },
    {
        "submitBlockNumber": 9527494,
        "confirmBlockNumber": 9527496,
        "sampleGasPrice": "4900620208",
        "recommendedGasPrice": "4900620208",
        "usedGasPrice": "4900620208",
        "hash": "0x15a2c77abeb3da02da6da4b31086f646ff28df72e71efe075a7519db25199015"
    },
    {
        "submitBlockNumber": 9527506,
        "confirmBlockNumber": 9527508,
        "sampleGasPrice": "4900620208",
        "recommendedGasPrice": "4900620208",
        "usedGasPrice": "4900620208",
        "hash": "0xefad83420f9105373beb8495573b2172dcad3e990f17ffc85da308b89bdb8f15"
    },
    {
        "submitBlockNumber": 9527520,
        "confirmBlockNumber": 9527522,
        "sampleGasPrice": "7350930312",
        "recommendedGasPrice": "4900620208",
        "usedGasPrice": "7350930312",
        "hash": "0xdf65be49da1455407b35f506c7368759a3a5027f668c102f5096ebb148594d3a"
    },
    {
        "submitBlockNumber": 9527526,
        "confirmBlockNumber": 9527527,
        "sampleGasPrice": "4900620207",
        "recommendedGasPrice": "4900620208",
        "usedGasPrice": "4900620208",
        "hash": "0x8dc488250563f360a7fca7708d95e1191870bc773ff3c5b363652415295cf38a"
    },
    {
        "submitBlockNumber": 9527535,
        "confirmBlockNumber": 9527536,
        "sampleGasPrice": "4900620208",
        "recommendedGasPrice": "4900620208",
        "usedGasPrice": "4900620208",
        "hash": "0x77129e87f20341e68a974d896821185332d755de7cfa5291ae26337a5f75d96d"
    },
    {
        "submitBlockNumber": 9527539,
        "confirmBlockNumber": 9527540,
        "sampleGasPrice": "4900620208",
        "recommendedGasPrice": "4900620208",
        "usedGasPrice": "4900620208",
        "hash": "0xe49174cb902ed3d6210850d3ffb2efb366d4c074539413277a289633db234473"
    },
    {
        "submitBlockNumber": 9527547,
        "confirmBlockNumber": 9527548,
        "sampleGasPrice": "4900620208",
        "recommendedGasPrice": "4900620208",
        "usedGasPrice": "4900620208",
        "hash": "0x2430fdf2316908bc49f92d36dafda22a841f910e77691b8ef9443b4e5b5ae98e"
    },
    {
        "submitBlockNumber": 9527550,
        "confirmBlockNumber": 9527554,
        "sampleGasPrice": "4900620208",
        "recommendedGasPrice": "4900620208",
        "usedGasPrice": "4900620208",
        "hash": "0x59b7298aa8b93d967e2d92d75af67a4bb7e804903694857b2df4f1578754bef0"
    },
    {
        "submitBlockNumber": 9527558,
        "confirmBlockNumber": 9527560,
        "sampleGasPrice": "4000000000",
        "recommendedGasPrice": "4900620208",
        "usedGasPrice": "4900620208",
        "hash": "0xf18b2e39fd58cbafa89f8a13a1783111a16a99f51e2d0745d168da9a79547b3f"
    }
]
```
