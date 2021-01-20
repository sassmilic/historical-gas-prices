import json
import multiprocessing
import os

#INFURA_API_KEY = os.getenv('INFURA_API_KEY')
#INFURA_PROVIDER = f"wss://mainnet.infura.io/ws/v3/{INFURA_API_KEY}"
NODE_IP_ADDR = os.getenv('NODE_IP_ADDR')

# configs for scraping transaction prices
SAMPLE_PERCENT = 1
NTHREADS = multiprocessing.cpu_count()
TIMEZONE = 'utc'
