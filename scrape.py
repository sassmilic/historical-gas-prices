#!/usr/local/bin/python3
import csv
from datetime import datetime, timedelta, timezone
import logging
import numpy as np
from numpy.random import choice
import pandas as pd
import queue
import threading
import time
from tqdm import tqdm
from multiprocessing import Pool

# uncomment to debug deadlock issues
# from hanging_threads import start_monitoring
# monitoring_thread = start_monitoring()

from util import LockedIterator, connect, get_first_eth_block_at

from config import (
    NTHREADS,
    SAMPLE_PERCENT,
)

logging.basicConfig(level=logging.INFO)

WEB3 = connect()

to_unixtime = lambda dt: (dt - datetime(1970, 1, 1)).total_seconds()
dt_to_str = lambda dt: dt.strftime('%Y-%m-%d')
do_select = lambda: choice([True, False], 1, p=[SAMPLE_PERCENT/100, 1 - SAMPLE_PERCENT/100])[0]

# keep track of progress via progress bar
PBAR = None

def scrape_prices(dt_from, dt_to=None, outfile='gas_prices.csv'):

    web3 = connect()

    block1 = get_first_eth_block_at(to_unixtime(dt_from))

    if dt_to:
        block2 = get_first_eth_block_at(to_unixtime(dt_to))
    else:
        dt_to = datetime.now() # for logging purposes
        block2 = web3.eth.getBlock('latest')

    block_nums = range(block1['number'], block2['number'] + 1)

    ##
    ## producer - consoomer pattern
    ##

    txn_queue = queue.Queue()
    price_queue = queue.Queue()

    # initialize progress bar
    global PBAR
    # approximate total number of txns to process
    txns_per_sec = 15 # optimistic; i.e. upper bound
    secs = (dt_to - dt_from).seconds
    approx_total_txns = secs * txns_per_sec * SAMPLE_PERCENT / 100
    PBAR = tqdm(total=int(approx_total_txns))

    # Create consumers
    # - consoomers read from txn hash queue and query transactions for prices
    for i in range(NTHREADS - 1):
        t = threading.Thread(target=consoomer, args=(i, txn_queue, price_queue))
        # thread killed once main program exits
        t.daemon = True
        t.start()

    # create producer
    # producer queries for block numbers and collects txn hashes
    prod = threading.Thread(target=producer, args=(block_nums, txn_queue, price_queue))
    prod.start()
    prod.join()

    with open(outfile, 'w') as f:
        f.write(f"# Sampling {SAMPLE_PERCENT}% of transactions\n")
        f.write(f"# from {dt_from} to {dt_to}\n")

        fieldnames = ['blockNum', 'txnID', 'gasPrice']
        writer = csv.writer(f, delimiter='\t')

        writer.writerow(fieldnames)

        while not price_queue.empty():
            block_num, txn_id, gas_price = price_queue.get()
            txn_id = txn_id.hex() # convert to a string
            writer.writerow([block_num, txn_id, gas_price])

    logging.info("Done.")


# Function called by the producer thread
def producer(block_nums, txn_queue, price_queue):
    web3 = connect()

    for block_num in block_nums:

        block = web3.eth.getBlock(block_num)
        date = datetime.utcfromtimestamp(block['timestamp'])

        for txnhash in block['transactions']:
            # only add SAMPLE_PERCENT of transactions to txn queue
            if do_select():
                txn_queue.put((block_num, txnhash))

    '''
    producer thread waits for consumer threads.
    Maybe not the most elegant solution, but it does decouple
    main thread from consumer threads so the main only needs
    to keep track of (i.e. "join") the one producer thread.
    '''

    while not txn_queue.empty():
        # wait for price queue to populate
        # TODO: might still fail with lots of lag time on API calls
        # TODO: approximate sleep time based on query params
        time.sleep(30)

    logging.info("Transaction queue is empty.")

    '''
    NOTE: Just because the txn queue is empty,
    doesn't mean the operation is over. The last
    "popped" transaction might still be in
    processing by one of the consumer threads.

    To ensure this isn't the case, we make sure
    the price queue hasn't changed since we last
    checked.
    '''
    qsize = None
    if not qsize or qsize != price_queue.qsize():
        # TODO: might still fail with lots of lag time on API calls
        time.sleep(10)

    PBAR.close()
    return

def consoomer(i, txn_queue, price_queue):
    web3 = connect()
    while True:
        if not txn_queue.empty():
            block_num, txnhash = txn_queue.get()
            txn = web3.eth.getTransaction(txnhash)
            t = (block_num, txnhash, txn['gasPrice'])
            price_queue.put(t)

            # update progress bar
            PBAR.update(1)

if __name__ == '__main__':
    from_datestr = '2021-01-19'
    dt_from = datetime.strptime(from_datestr, "%Y-%m-%d")
    to_datestr = dt_to_str(datetime.now())

    outfile = f'gas_prices_{from_datestr}_{to_datestr}_{SAMPLE_PERCENT}%-sampling.csv'

    scrape_prices(dt_from, dt_to=dt_to,  outfile=outfile)

