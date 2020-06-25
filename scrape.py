from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
import threading
import time
from multiprocessing import Pool

from util import LockedIterator, connect, get_first_eth_block_at

from config import (
    PERCENTILE_GRANULARITY,
    NTHREADS
)

to_unixtime = lambda dt: (dt - datetime(1970, 1, 1)).total_seconds()
dt_to_str = lambda dt: dt.strftime('%Y-%m-%d')

# TODO: multithreading
# TODO: configurable aggregation granularity -- currently set at 1 day
# TODO: should I continue weighing gas price by total gas used in transaction?
# TODO: timezones

class Transaction:
    '''
    Keeping only info relevant to gas prices.
    '''
    def __init__(self, block_number, gas, gas_price):
        self.block_number = block_number
        self.gas = gas
        self.gas_price = gas_price

def scrape_prices(dt_from, dt_to=None, outfile='gas_prices.csv'):
   
    web3 = connect()

    ts = to_unixtime(dt_from)
    block1 = get_first_eth_block_at(ts)

    if dt_to:
        ts2 = to_unixtime(dt_to)
        block2 = get_first_eth_block_at(ts2)
    else:
        block2 = web3.eth.getBlock('latest')

    percents =  np.linspace(0, 100, PERCENTILE_GRANULARITY + 1, endpoint=True)
    percents = percents[1:] # remove 0
    
    columns = ['day', 'total_txns', *percents]
    result = {col:[] for col in columns}

    block_num_gen = range(block1['number'], block2['number'] + 1) 

    current_date = None # granularity at day-level
    txns = []

    def _aggregate():
        result['day'].append(dt_to_str(current_date))
        result['total_txns'].append(len(txns))
        pcts = np.percentile([t.gas_price / t.gas for t in txns], percents)
        for k,v in zip(percents, pcts):
            result[k].append(v)

    for i,block_num in enumerate(block_num_gen):

        if i > 10:
            break

        block = web3.eth.getBlock(block_num)

        date = datetime.utcfromtimestamp(block['timestamp'])
        if not current_date:
            current_date = date


        # aggregate per day
        if date - current_date >= timedelta(days=1):
            current_date = date
            _aggregate()
            txns = []

        for txnhash in block['transactions']:
            txns.append(__parse_transaction(txnhash))

    df = pd.DataFrame(result)
    df.to_csv(outfile, columns=columns)

def __parse_transaction(txnhash):
    web3 = connect()
    txn = web3.eth.getTransaction(txnhash)
    return Transaction(txn['blockNumber'], txn['gas'], txn['gasPrice'])


if __name__ == '__main__':
    datestr = '2020-06-20'
    dt_from = datetime.strptime(datestr, "%Y-%m-%d")
    scrape_prices(dt_from)

