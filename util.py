import time
import threading
import warnings
from web3 import Web3

from config import (
    NODE_IP_ADDR
)

if not NODE_IP_ADDR:
    warnings.warn("Address of Ethereum node is missing.")

class LockedIterator(object):
    # from: https://stackoverflow.com/questions/1131430/are-generators-threadsafe
    def __init__(self, it):
        self.lock = threading.Lock()
        self.it = it.__iter__()

    def __iter__(self): return self

    def next(self):
        self.lock.acquire()
        try:
            return self.it.next()
        finally:
            self.lock.release()

def connect():
    return Web3(Web3.HTTPProvider(NODE_IP_ADDR))

def get_first_eth_block_at(ts):
    '''
    Return the first Ethereum block with timestamp less than or equal to timestamp ts.
    '''
    web3 = connect()

    current_time = time.time()
    latest_block = web3.eth.getBlock('latest')

    # block time for ethereum is ~15 seconds
    block_time = 15
    seconds_in_day = 86400

    ##
    ## First, narrow down search to within 24 hours
    ## This is done with heuristics derived from avg block time
    ##

    first_block = latest_block
    # check if `first_block` was mined before `timestamp`
    while first_block['timestamp'] - ts > 0:
        diff_days = (first_block['timestamp'] - ts) // seconds_in_day
        if diff_days == 0:
            diff_days = 0.5 # prevents potential infinite loop
        blocks_ago = diff_days * seconds_in_day // block_time
        blocks_ago = int(blocks_ago)
        first_block_num = first_block['number'] - blocks_ago
        first_block = web3.eth.getBlock(first_block_num)

    ##
    ## Next, do binary search to get exact block number
    ##

    # get block approx 24 hours ahead of `first_block`
    # using 36 instead of 24 to have a buffer than ensures `block24` timestamp >= `ts`
    hours_ahead = 36
    block_num = first_block['number'] + hours_ahead * seconds_in_day // block_time
    # sometimes latest block will return an error when using its number in `getBlock`
    # probably due to general asynchrony in the network, hence buffer
    buffer_ = 10
    block_num = min(web3.eth.getBlock('latest')['number'] - buffer_, block_num)
    block24 = web3.eth.getBlock(block_num)
    assert block24['timestamp'] > ts

    return __binary_search(web3, ts, first_block, block24)


def __binary_search(web3, ts, block1, block2):

    while block1['number'] < block2['number']:

        mid = web3.eth.getBlock((block1['number'] + block2['number']) // 2 + 1)

        if mid['timestamp'] == ts:
            # very unlikely
            return mid

        elif mid['timestamp'] < ts:
            block1 = mid

        else:
            # mid['timestamp'] > ts:
            block2 =  web3.eth.getBlock(mid['number'] - 1)

    return block1

