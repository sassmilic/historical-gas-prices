import time
import unittest

import util

class TestGetFirstEthBlockAt(unittest.TestCase):
    
    def setUp(self):
        self.web3 = util.connect()

    def test_24_hours_ago(self):
        """
        Test getting eth block from 24 hours ago
        """
        ts = int(time.time()) - 24 * 60 * 60 
        block = util.get_first_eth_block_at(ts)
        block_after = self.web3.eth.getBlock(block['number'] + 1)
        self.assertTrue(block['timestamp'] <= ts and ts < block_after['timestamp'])

if __name__ == '__main__':
    unittest.main()
