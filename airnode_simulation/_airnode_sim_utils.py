import datetime
import glob
import math
import random
import re

import numpy as np
import pandas as pd
import seaborn as sns
from tqdm.notebook import tqdm
import matplotlib.pyplot as plt

API3_PURPLE = '#7963B2'
API3_EMERALD = '#7CE3CB'

def load_data(file_patterns):
    fnames = []
    for p in file_patterns:
        fnames.extend(glob.glob(p))

    print(f"{len(fnames)} total files.")

    # concat all data into one dataframe
    l = []
    for fname in fnames:
        df = pd.read_csv(fname, index_col=None, delimiter='\t')
        l.append(df)

    df = pd.concat(l, axis=0, ignore_index=True)

    # convert wei to gwei
    df['gasPrice'] = df['gasPrice'] / 1_000_000_000

    # remove last block num just in case (files are cut off)
    df = df[df.blockNum != df.blockNum.max()]

    # sort
    df = df.sort_values(by=['blockNum'])

    # just in case: drop duplicates
    df = df.drop_duplicates()

    df = df.reset_index(drop=True)

    return df

def airnode_sim(df, wake_up_times, gas_price_selection='boosted'):
    # store results
    result = {
        'wakeup_ts': [], # timestamp of Airnode 'wake up time'
        'method': [],
        'gasPrice': [], # gas prices of response txns
        #'mined?': [], # whether or not the txn was mined within the minute
        'confirmation_block_num': [], # the number of the block in which the txn was mined
        'confirmation_block_seconds': [], # the number seconds it took the txn to get mined
        'next_block_percentiles': []
    }

    if not isinstance(gas_price_selection, list):
        gas_price_selection = [gas_price_selection]

    # TODO: add some lag to airnode response e.g. 1-5 seconds

    def _get_recommended(df, block_num):
        # by default, recommonded gas price given by providers
        # is the 60th percentile of gas prices in last 20 blocks
        prev20 = set(range(block_num - 20, block_num))
        df_slice = df[df['blockNum'].isin(prev20)]
        return np.percentile(df_slice['gasPrice'], 60)

    # queue of block numbers
    block_queue = list(df['blockNum'].unique())
    block_queue.sort() # just in case

    # dataframe containing only min gas price per block
    df_min = df.groupby('blockNum').min()[['gasPrice', 'timeStamp']]
    df_max = df.groupby('blockNum').max()[['gasPrice', 'timeStamp']]

    ### 1. Airnode wakes up
    prev = block_queue.pop(0)
    for i,ts in tqdm(list(enumerate((wake_up_times)))):

        # add lag: 3 seconds, pretty conservative
        ts += 3

        ### 2. Checks most recently mined block
        curr = block_queue.pop(0)

        # ensure: current_block.ts <= ts < next_block.ts
        while df_min.loc[curr].timeStamp <= ts:
            prev = curr
            curr = block_queue.pop(0)

        current_block = prev
        next_block = curr

        ts1 = df_min.loc[current_block].timeStamp
        ts2 = df_min.loc[next_block].timeStamp

        assert ts1 <= ts < ts2

        if ts2 - ts > 60:
            for method, chosen_gas_price in zip(gas_price_selection, chosen_gas_prices):
                # next block is 60 seconds after `ts`
                # our transaction woulnd't get mined regardless
                result['wakeup_ts'].append(ts)
                result['method'].append(method)
                result['gasPrice'].append(None)
                #result['mined?'].append(False)
                result['confirmation_block_num'].append(None)
                result['confirmation_block_seconds'].append(None)
                result['next_block_percentiles'].append(ps)
                continue

        chosen_gas_prices = []

        for gps in gas_price_selection:
            ### 3. Select a gas price for the transaction
            if gps == 'recommended':
                chosen_gas_prices.append(_get_recommended(df, current_block))

            elif gps == 'rand1':
                ### 3a. Randomly selects a txn from block
                ### 3b. The gas price of that txn is selected by Airnode.
                gas_prices = df[df['blockNum'] == current_block]['gasPrice'].values
                chosen_gas_price = random.choice(gas_prices)
                ### 3c. remove extreme values via recommended gas price
                rec_price = _get_recommended(df, current_block)

                if chosen_gas_price < rec_price:
                    chosen_gas_prices.append(rec_price)

                elif chosen_gas_price > 2 * rec_price:
                    chosen_gas_prices.append(2 * rec_price)

            elif gps == 'rand3':
                # performs pretty bad
                gas_prices = list(df[df['blockNum'] == current_block]['gasPrice'].values)
                if len(gas_prices) < 3:
                    chosen_gas_prices.append(max(gas_prices))
                else:
                    chosen_gas_prices.append(sorted(random.sample(list(gas_prices), 3))[1])

            elif gps.startswith('boosted'):
                boost_x = float(re.match('boosted_(.*)', gps).group(1))
                chosen_gas_prices.append(boost_x * _get_recommended(df, current_block))

            else:
                raise Exception('unknown gas price selection technique')

        ### EVALUATE:
        # Is this gas price *strictly greater* than the min gas price
        # in all blocks mined in the next minute??

        # get all blocks mined within the minute
        # NOTE: don't pop!
        nxt_blocks = [next_block]
        j = 0
        while df_min.loc[block_queue[j]].timeStamp <= ts + 60:
            nxt_blocks.append(block_queue[j])
            j += 1

        # don't include blocks that are currently being mined
        nxt_blocks = [b for b in nxt_blocks if df_min.loc[b].timeStamp > 10 + ts]

        for i,b in enumerate(nxt_blocks):

            nxt_gas_prices = df[df['blockNum'] == b].gasPrice.tolist()
            nxt_gas_prices.sort()

            ps = [_percentile(nxt_gas_prices, p) for p in [0, 25, 50, 75, 100]]

            for method, chosen_gas_price in zip(gas_price_selection, chosen_gas_prices):

                assert ps[0] == df_min.loc[b]['gasPrice']
                assert ps[-1] == df_max.loc[b]['gasPrice']

                # update results
                result['wakeup_ts'].append(ts)
                result['method'].append(method)
                result['gasPrice'].append(chosen_gas_price)
                #result['mined?'].append(True)
                result['confirmation_block_num'].append(i + 1)
                result['confirmation_block_seconds'].append(df_min.loc[b]['timeStamp'] - ts)
                result['next_block_percentiles'].append(ps)

    df_results = pd.DataFrame(result)
    return df_results

def _percentile(l, p):
    i = math.floor(len(l) * p / 100)
    i = min(len(l) - 1, i)
    return l[i]

def plot1(df, lower_cap=None, upper_cap=None):
    _, ax = plt.subplots(1, 1, figsize=(15,10))

    b_start = 9656650
    blocks = range(b_start, b_start + 20)

    df = df[df['blockNum'].isin(blocks)]

    if lower_cap:
        df = df[lower_cap < df['gasPrice']]

    if upper_cap:
        df = df[df['gasPrice'] < upper_cap]

    g = sns.boxplot(
        ax=ax,
        x="blockNum",
        y="gasPrice",
        #height=1,
        #aspect=1,
        color=API3_PURPLE,
        data=df
    )

    g.set_xticks([])
    g.set(xlabel='', ylabel='gas price (Gwei)')
    #plt.xticks(rotation=45)
    g.set_title(f"Distribution of gas price in consecutive blocks (during a peak period around {df['hour'].iloc[0]}:00)");

def plot_gas_prices(df):
    start_ts = df.iloc[0]['timeStamp']
    end_ts = df.iloc[-1]['timeStamp']

    def percentile(n):
        def percentile_(x):
            return np.percentile(x, n)
        percentile_.__name__ = 'percentile_%s' % n
        return percentile_

    df_agg = df.groupby('blockNum')['gasPrice'].aggregate(
        ['median', 'mean', 'std', percentile(10), percentile(25), percentile(75), percentile(90)]
    )
    df_agg = df_agg.reset_index()

    # overlay individual median points with [25, 75] percentile range
    lower_bound = np.array(df_agg['percentile_10'])
    upper_bound = np.array(df_agg['percentile_90'])

    _, ax = plt.subplots(1, 1, figsize=(20,10))

    g = sns.scatterplot(x="blockNum", y="median", data=df_agg, s=3, color="black")
    plt.fill_between(df_agg['blockNum'], lower_bound, upper_bound, alpha=.2, color=API3_PURPLE);
    plt.ylim(0, 350);

    to_date_str = lambda ts: datetime.datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

    g.set(
        xlabel='',
        ylabel='gas price (Gwei)',
        xticks=[df_agg['blockNum'].iloc[0], df_agg['blockNum'].iloc[-1]],
        xticklabels=[to_date_str(start_ts), to_date_str(end_ts)]
    )

    g.set_title(f'Median gas prices around the time of Black Thursday overlaid with [25th, 75th] percentile intervals');
