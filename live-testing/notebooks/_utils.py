"""Utility functions for live test analysis"""

from typing import cast, Set
import bisect
import glob
import json
import math
import os
import re
import shelve
import threading

from tqdm.notebook import tqdm
from web3.auto import w3
from web3.types import (
    RPCEndpoint,
)
import numpy as np
import pandas as pd
import web3
pd.options.mode.chained_assignment = None

#####################
## connect to node ##
#####################

class EmptyProvider(Exception):
    # pylint: disable=C0115
    pass

if "WEB3_PROVIDER_URI" not in os.environ:
    raise EmptyProvider("Environment variable WEB3_PROVIDER_URI is not set.")

assert w3.isConnected(), "problem connecting to node"

######################
## initialize cache ##
######################

def _init_cache():
    def _should_cache(method, params, response):
        if 'error' in response:
            return False
        if 'result' not in response:
            return False
        if response['result'] is None:
            return False
        return True

    rpc_whitelist = cast(Set[RPCEndpoint], {
        'eth_getBlockByHash',
        'eth_getBlockByNumber',
        'eth_getTransactionByHash',
        'eth_getTransactionByBlockHashAndIndex',
        'eth_getTransactionByBlockNumberAndIndex',
        'eth_getTransactionReceipt',
    })

    # put in persistent dict-like database via shelve.py
    db = shelve.open('api_cache')
    # create callable
    cache_class = lambda: db
    simple_cache = web3.middleware.construct_simple_cache_middleware(
        cache_class, rpc_whitelist, _should_cache
    )
    w3.middleware_onion.add(simple_cache)

_init_cache()

####################
## important note ##
####################
"""
NOTE: shelve.py does NOT support concurrent processes
- pandas `apply` is computed in parallel
- this necessitates a lock when any API calls are made in an `apply` call
- kinda ugly but must be done
"""

CACHE_LOCK = threading.Lock()

def load_live_test_data():
    """
    Load json files that are the log/output files of ../src/live-test.js.
    """
    file_pattern = '../txes_(.*)\.json'

    json_files = glob.glob('../txes_*.json')

    print(f'Reading from {json_files}')

    dfs = []

    for filename in json_files:
        method = re.match(file_pattern, filename).group(1)
        with open(filename, 'r') as data_file:
            json_data = json.loads(data_file.read())

        df = pd.DataFrame.from_records(json_data) #pylint: disable=C0103
        df['method'] = method

        dfs.append(df)

    df = pd.concat(dfs, ignore_index=True) #pylint: disable=C0103
    return df

def convert_to_int(df):
    """
    Inplace convert all relevant columns to ints.
    """
    # convert floats to ints
    for col in [
        'confirmBlockNumber',
        'confirmTimestamp',
        'confirmations',
        'createTimestamp',
        'recommendedGasPrice',
        'sampleGasPrice',
        'submitBlockNumber',
        'submitTimestamp',
        'usedGasPrice']:

        df[col].replace({None: float('nan')}, inplace=True)
        df[col] = df[col].astype(pd.Int64Dtype())

def validate(df, pbar=False):
    '''
    Validate the main `df` with blockchain data.

    For each txn in the df:

    1.  Check the timestamp of the most recent block
        when txn was submitted (submit block).
    2.  Check the block when txn was mined (confirm block).
    3.  Check the timestamp of the confirm block.
    4.  Add confirmation time.
    5.  Assert gas price is accurately reported.
    6.  Convert everything to int.
    '''

    if pbar:
        pbar = tqdm(total=df.shape[0])

    df = df.apply(_validate_row, axis=1, pbar=pbar)

    convert_to_int(df)

    return df

def _validate_row(row, pbar):
    if pbar:
        pbar.update(1)

    ##
    ## check txn hash
    ##

    txn_hash = row['hash']
    if not txn_hash:
        # unmined txn
        return row

    ##
    ## check submit block
    ##

    bx = row['submitBlockNumber']
    # this should not be empty
    assert bx
    assert not math.isnan(bx)

    with CACHE_LOCK:
        block = w3.eth.getBlock(int(bx))

    row['submitTimestamp'] = _check_submit_block_ts(block, row['submitTimestamp'])

    ##
    ## check confirm block
    ##

    # get txn from blockchain
    try:

        with CACHE_LOCK:
            txn = w3.eth.getTransaction(txn_hash)

    except web3.exceptions.TransactionNotFound:
        print(f"Txn {txn_hash} not found.")
        return

    row['confirmBlockNumber'] = _check_confirm_block_txn(txn, row['confirmBlockNumber'])

    # get confirm block from blockchain
    with CACHE_LOCK:
        block = w3.eth.getBlock(row['confirmBlockNumber'])

    row['confirmTimestamp'] = _check_confirm_block_ts(txn_hash, block, row['confirmTimestamp'])

    # add number of confirmations
    row['confirmations'] = int(row['confirmBlockNumber'] - row['submitBlockNumber'])

    # `usedGasPrice` should *not* be empty, and there shouldn't be a discrepency
    assert row['usedGasPrice'] is not None
    assert row['usedGasPrice'] != float('nan')
    row['usedGasPrice'] = int(row['usedGasPrice'])
    assert row['usedGasPrice'] == txn.gasPrice#, (row['usedGasPrice'], txn.gasPrice)

    # convert timestamp to s
    # javascript uses ms by default
    row['createTimestamp'] = row['createTimestamp'] // 1000

    return row

def _check_submit_block_ts(block, ts_reported):
    """Check submit block timestamp."""
    ts = block.timestamp

    if math.isnan(ts_reported):
        #print(f"Warning: empty submit timestamp for {txn_hash}")
        pass # warning too common

    elif ts != ts_reported:
        print(f"Warning: unmatching timestamps for Block {block.number}: {ts}, {ts_reported}")

    return ts

def _check_confirm_block_txn(txn, bx_reported):
    """Check that `txn` was in fact mined in `block`."""

    # might be empty
    if not bx_reported or math.isnan(bx_reported):
        # get block number from txn hash
        bx = int(txn.blockNumber)
    else:
        assert bx_reported == txn.blockNumber
        bx = txn.blockNumber

    return bx

def _check_confirm_block_ts(txn_hash, block, ts_reported):
    """Check confirm block timestamp."""
    ts = block.timestamp

    if math.isnan(ts_reported):
        print(f"Warning: empty confirm timestamp for {txn_hash}")

    if ts != ts_reported:
        print(f"Warning: matched timestamps for Block {block.number}: {ts}, {ts_reported}")

    return ts

def get_mined_df(df, pbar=False):
    """
    Given the DataFrame `df` representing raw data from '../src/live-test.js',
    return a DataFrame containing blocks where given txns are mined/unmined.
    Columns of resulting DataFrame:
    - hash
    - usedGasPrice
    - confirmations
    - mined_block
    - unmined_blocks
    """
    def _get_unmined_blocks(row, pbar, delay=10):
        if pbar:
            pbar.update(1)

        ts1 = row['createTimestamp']

        if not math.isnan(row['confirmTimestamp']):
            ts2 = row['confirmTimestamp']
        else:
            ts2 = ts1 + 60

        # get all blocks mined in (ts + delay, ts + 60)

        # NOTE: we add a slight delay to discount blocks that
        #       are currently being mined; ethereum block time
        #       is ~10-20 seconds

        bxs = _get_blocks_in_range(ts1 + delay, ts2, int(row['submitBlockNumber']))

        return pd.Series(
            [
                row['hash'], row['usedGasPrice'],  row['confirmations'],
                row['confirmBlockNumber'], bxs],
            index=['hash', 'usedGasPrice', 'confirmations', 'mined_block', 'unmined_blocks']
        )

    if pbar:
        pbar = tqdm(total=df.shape[0])

    return df.apply(_get_unmined_blocks, axis=1, args=(pbar,))

def _get_blocks_in_range(ts1, ts2, block_hint):
    bxs = []

    with CACHE_LOCK:
        block = w3.eth.getBlock(block_hint)

    while block.timestamp < ts2:
        if block.timestamp > ts1:
            bxs.append(block.number)

        with CACHE_LOCK:
            block = w3.eth.getBlock(block.number + 1)

    return bxs

def get_historical_transaction_data():
    """
    Get historical data.

    Columns: ['blockNum', 'txnHash', 'gasPrice']
    """
    file_pattern = '../../output_*'
    dfs = []
    for fname in glob.glob(file_pattern):
        with open(fname) as f:
            dfs.append(pd.read_csv(f, delimiter='\t', names=['blockNum', 'txnHash', 'gasPrice']))

    df = pd.concat(dfs)
    df.drop_duplicates(inplace=True)
    df.reset_index(drop=True, inplace=True)
    #df.drop('txnHash', inplace=True, axis=1)
    df.sort_values('blockNum', inplace=True)

    return df

def get_percentile_df(df_mined, df_hist, pbar=False):
    """
    TODO
    """
    def _get_percentile(row, col, pbar=None):
        if pbar:
            pbar.update(1)
        bxs = row[col]
        if not isinstance(bxs, list):
            bxs = [bxs]
        ps = []
        for bx in bxs:
            gas_prices = df_hist[df_hist.blockNum == bx]['gasPrice']
            gas_prices = gas_prices.tolist()
            if len(gas_prices) == 0:
                gas_prices = _get_gas_prices(bx)
                if len(gas_prices) == 0:
                    ps.append(float('nan'))
                    continue
            #gas_prices = list(map(int, gas_prices))
            gas_prices.sort()
            #print(gas_prices)
            p = bisect.bisect(gas_prices, int(row['usedGasPrice'])) / len(gas_prices) * 100
            # round for easier analysis
            p = round(p, 2)
            ps.append(p)
        if not isinstance(row[col], list):
            ps = ps[0]
        row[col + '_percentiles'] = ps
        return pd.Series(row)

    if pbar:
        pbar = tqdm(total=df_mined.shape[0])

    df_percentile = df_mined.apply(_get_percentile, axis=1, args=('unmined_blocks', pbar))

    pbar = tqdm(total=df_percentiles.shape[0])
    df_percentiles = df_percentiles.apply(_get_percentile, axis=1, args=('mined_block', pbar))

    return df_percentiles

def _get_gas_prices(bx):
    """
    Get all gas prices for txns in `bx`.
    """
    prices = []
    try:

        with CACHE_LOCK:
            block = w3.eth.getBlock(bx)

    except TypeError:
        return []

    for txn_hash in block.transactions:

        with CACHE_LOCK:
            txn = w3.eth.getTransaction(txn_hash)

        prices.append(txn.gasPrice)

    return prices
