from datetime import datetime, timedelta, timezone
import numpy as np
from numpy.random import choice
import pandas as pd
import queue
import threading
import time
from multiprocessing import Pool

from hanging_threads import start_monitoring
monitoring_thread = start_monitoring()

from util import LockedIterator, connect, get_first_eth_block_at

from config import (
    PERCENTILE_GRANULARITY,
    NTHREADS,
    SAMPLE_PERCENT,
)

WEB3 = connect()

to_unixtime = lambda dt: (dt - datetime(1970, 1, 1)).total_seconds()
dt_to_str = lambda dt: dt.strftime('%Y-%m-%d')
do_select = lambda: choice([True, False], 1, p=[SAMPLE_PERCENT/100, 1 - SAMPLE_PERCENT/100])[0]

# TODO: multithreading
# TODO: configurable aggregation granularity -- currently set at 1 day
# TODO: should I continue weighing gas price by total gas used in transaction?
# TODO: timezones

def scrape_prices(dt_from, dt_to=None, outfile='gas_prices.csv'):
   
    web3 = connect()

    ts = to_unixtime(dt_from)
    block1 = get_first_eth_block_at(ts)

    if dt_to:
        ts2 = to_unixtime(dt_to)
        block2 = get_first_eth_block_at(ts2)
    else:
        block2 = web3.eth.getBlock('latest')

    block_nums = range(block1['number'], block2['number'] + 1) 

    ##
    ## producer - consoomer pattern
    ##

    txn_queue = queue.Queue()
    price_queue = queue.Queue()
    
    # Create consumers
    # - consoomers read from txn hash queue and query transactions for prices
    for i in range(NTHREADS - 1):
        t = threading.Thread(target=consoomer, args=(i, txn_queue, price_queue))
        # thread killed once main program exits
        t.daemon = True
        t.start() 
   
    # create producer
    # producer queries for block numbers and collects txn hashes
    result = {}
    prod = threading.Thread(target=producer, args=(block_nums, txn_queue, price_queue, result))
    prod.start() 
    prod.join()

    print("RESULT")
    print(result)
    df = pd.DataFrame(result)
    df.to_csv(outfile, header=True)


# Function called by the producer thread
def producer(block_nums, txn_queue, price_queue, agg_result):
    web3 = connect()
    
    percents =  np.linspace(0, 100, PERCENTILE_GRANULARITY + 1, endpoint=True)
    percents = percents[1:] # remove 0
  
    columns = ['day', 'total_txns', *percents]
    for col in columns:
        agg_result[col] = []

    current_date = None # granularity at day-level

    for block_num in block_nums:
        
        block = web3.eth.getBlock(block_num)
        date = datetime.utcfromtimestamp(block['timestamp'])
       
        print(date)

        if not current_date:
            current_date = date
        
        # aggregate per day
        if date - current_date >= timedelta(days=1):
            current_date = date
            __aggregate(price_queue, txn_queue, agg_result, percents, current_date)

        for txnhash in block['transactions']:
            # only add SAMPLE_PERCENT of transactions to txn queue
            if do_select():
                txn_queue.put(txnhash)

def __aggregate(price_queue, txn_queue, agg_result, percents, current_date):
    print('aggregating', dt_to_str(current_date))
    prices = []
    count = 0

    # this will block until consumer threads are done
    while not (price_queue.empty() and txn_queue.empty()):
        if not price_queue.empty():
            prices.append(price_queue.get())
            count += 1
        else:
            # wait for price queue to populate
            time.sleep(1)
    
    agg_result['day'].append(dt_to_str(current_date))
    agg_result['total_txns'].append(count)
    pcts = np.percentile(prices, percents)
    for k,v in zip(percents, pcts):
        # dicts and lists are threadsafe, I think
        agg_result[k].append(v)

def consoomer(i, txn_queue, price_queue):
    web3 = connect()
    while True:
        try:
            txnhash = txn_queue.get()
            txn = web3.eth.getTransaction(txnhash)
            price_queue.put(txn['gasPrice'] / txn['gas'])
        except queue.Empty:
            pass 

if __name__ == '__main__':
    datestr = '2020-06-20'
    dt_from = datetime.strptime(datestr, "%Y-%m-%d")
    scrape_prices(dt_from)

