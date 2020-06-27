import json
import multiprocessing

INFURA_URL = "https://mainnet.infura.io/v3/87dde21eb7704f8c82f3b51aa58653d0" #delet
INFURA_PROVIDER = "wss://mainnet.infura.io/ws/v3/87dde21eb7704f8c82f3b51aa58653d0" #delet

# configs for scraping transaction prices
PERCENTILE_GRANULARITY = 20
SAMPLE_PERCENT = 1
NTHREADS = multiprocessing.cpu_count()
TIMEZONE = 'utc'
