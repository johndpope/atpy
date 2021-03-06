import threading
import unittest

from atpy.data.iqfeed.iqfeed_bar_data_provider import *
from atpy.data.latest_data_snapshot import LatestDataSnapshot
from pyevents.events import AsyncListeners


class TestIQFeedBarData(unittest.TestCase):
    """
    IQFeed bar data test, which checks whether the class works in basic terms
    """

    def test_provider(self):
        listeners = AsyncListeners()

        with IQFeedBarDataListener(listeners=listeners, mkt_snapshot_depth=10, interval_len=60) as listener:
            # test bars
            e1 = {'GOOG': threading.Event(), 'IBM': threading.Event()}
            counters = {'GOOG': 0, 'IBM': 0}

            def bar_listener(event):
                if event['type'] == 'bar':
                    symbol = event['data']['symbol'][0]
                    self.assertTrue(symbol in ['IBM', 'GOOG'])
                    counters[symbol] += 1
                    if counters[symbol] >= listener.mkt_snapshot_depth:
                        e1[symbol].set()

            listeners += bar_listener

            # test market snapshot
            e3 = threading.Event()

            listeners += lambda event: [self.assertEqual(event['data'].shape[1], 9), e3.set()] if event['type'] == 'bar_market_snapshot' else None

            listeners({'type': 'watch_bars', 'data': {'symbol': ['GOOG', 'IBM'], 'update': 1}})

            for e in e1.values():
                e.wait()

    def test_listener(self):
        listeners = AsyncListeners()

        with IQFeedBarDataListener(listeners=listeners, interval_len=300) as listener:
            e1 = threading.Event()

            listeners += lambda event: [self.assertEqual(event['data']['symbol'][0], 'SPY'), e1.set()] if event['type'] == 'bar' else None

            listener.watch(symbol='SPY', interval_len=5, interval_type='s', update=1, lookback_bars=10)

            e1.wait()

    def test_latest_bars(self):
        listeners = AsyncListeners()

        with IQFeedBarDataListener(listeners=listeners, mkt_snapshot_depth=1000, interval_len=60) as listener:
            # test bars

            def bar_listener(event):
                if event['type'] == 'bar':
                    symbol = event['data']['symbol'][0]
                    self.assertTrue(symbol in ['IBM', 'GOOG'])
                    counters[symbol] += 1
                    if counters[symbol] >= listener.mkt_snapshot_depth:
                        e1[symbol].set()

            listeners += bar_listener

            # test market snapshot
            e3 = threading.Event()

            listeners += lambda event: [self.assertEqual(event['data'].shape[1], 9), e3.set()] if event['type'] == 'bar_market_snapshot' else None

            LatestDataSnapshot(listeners=listeners, event={'latest_bar_update', 'bar'}, fire_update=True, depth=100)

            e1 = {'GOOG': threading.Event(), 'IBM': threading.Event()}
            counters = {'GOOG': 0, 'IBM': 0}

            def snapshot_listener(event):
                if event['type'] == 'bar_snapshot' or event['type'] == 'latest_bar_update_snapshot':
                    data = event['data']
                    self.assertTrue(data.index.levels[0].is_monotonic)
                    self.assertGreater(len(data), 0)
                    counters[event['data']['symbol'][0]] += 1
                    if counters[event['data']['symbol'][0]] >= listener.mkt_snapshot_depth:
                        e1[event['data']['symbol'][0]].set()

            listeners += snapshot_listener

            listeners({'type': 'watch_bars', 'data': {'symbol': ['GOOG', 'IBM'], 'update': 1}})

            for e in e1.values():
                e.wait()


if __name__ == '__main__':
    unittest.main()
