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

####
####
# TODO:
# - store unixtime of block number

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

def scrape_prices(dt_from, dt_to=None):

    if not dt_to:
        dt_to = datetime.now() # for logging purposes

    outfile = f'gas_prices_{dt_to_str(dt_from)}_{dt_to_str(dt_to)}_{SAMPLE_PERCENT}%-sampling'
    logging.info(f'Writing to files prefixed with {outfile}')

    block_nums = get_block_numbers(dt_from, dt_to, SAMPLE_PERCENT)
    logging.info(f"Querying {len(block_nums)} blocks.")

    ##
    ## producer - consoomer pattern
    ##

    txn_queue = queue.Queue()
    price_queue = queue.Queue()

    # initialize progress bar
    global PBAR
    # approximate total number of txns to process
    txns_per_block = 170 # approximation
    approx_total_txns = len(block_nums) * txns_per_block

    logging.info(f"Approximately {approx_total_txns} txns to process.")

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
    prod = threading.Thread(target=producer, args=(block_nums, txn_queue, price_queue, outfile))
    prod.start()
    prod.join()

    logging.info("Done.")

def get_block_numbers(dt_from, dt_to, sample_percent, chunk_size=2):
    '''
    Get a sample of block numbers between dates `from_dt` to `to_dt`.
    - Only take a systematic sample of `sample_percent` from that range.
    - We have a constraint to ensure blocks are sampled in a contiguous
        chunk of `chunk_size`
    '''

    block1 = get_first_eth_block_at(to_unixtime(dt_from))
    block2 = get_first_eth_block_at(to_unixtime(dt_to))

    # all block numbers in this date range
    block_nums = list(range(block1['number'], block2['number'] + 1))

    n = len(block_nums)
    x = int(n * sample_percent / 100)

    skip = n // (x // chunk_size)

    first_blocks = range(block1['number'], block2['number'], skip)

    all_block_nums = []
    for b in first_blocks:
        for i in range(chunk_size):
            all_block_nums.append(b + i)

    return all_block_nums

def write_to_file(price_queue, outfile, part=None, ntxns=None):

    with open(outfile, 'w') as f:

        fieldnames = ['blockNum', 'txnID', 'gasPrice']
        writer = csv.writer(f, delimiter='\t')

        writer.writerow(fieldnames)

        if not ntxns:
            # write all txns
            while not price_queue.empty():
                block_num, txn_id, gas_price = price_queue.get()
                txn_id = txn_id.hex() # convert to a string
                writer.writerow([block_num, txn_id, gas_price])

        else:
            for _ in range(ntxns):
                block_num, txn_id, gas_price = price_queue.get()
                txn_id = txn_id.hex() # convert to a string
                writer.writerow([block_num, txn_id, gas_price])


# Function called by the producer thread
def producer(block_nums, txn_queue, price_queue, outfile):
    web3 = connect()

    for i, block_num in enumerate(block_nums):

        block = web3.eth.getBlock(block_num)
        date = datetime.utcfromtimestamp(block['timestamp'])

        for txnhash in block['transactions']:
            # add all txns to txn queue
            txn_queue.put((block_num, txnhash))

        # write results periodically to file
        # TODO: parameterize this
        if i // 50 and i % 50 == 0:
            part = i // 50
            logging.info(f"Writing part {part} to file.")
            write_to_file(price_queue, f"{outfile}_{part}.csv", part=part, ntxns=5000)

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

    write_to_file(price_queue, f"{outfile}_{i // 50 + 1}.csv", part=part)
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
            # TODO: add a sleep() if rps becomes an issue

if __name__ == '__main__':

    from_datestr = '2020-08-01'
    dt_from = datetime.strptime(from_datestr, "%Y-%m-%d")
    #df_from = dt_to - timedelta(minutes=30)
    scrape_prices(dt_from=dt_from, dt_to=datetime.now())
