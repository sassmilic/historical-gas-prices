# Tool to live-test Airnode gas price strategy

## Instructions

1. `npm install`
1. `npm run build`
1. Create a `.env` file similar to the [example.env](/live-testing/example.env) file. Note: the filename must be `.env`.
Note that you need multiple mnemonics for individually funded wallets to test methods in simultaneously.
1. `npm run deploy`
1. `npm run live-test` will calculate the has price and make a transaction periodically

New transactions will be recorded in `txes_${METHOD}.json`.
`Ctrl-C` when you've had enough.
