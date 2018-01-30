import random
import unittest

from atpy.backtesting.data_replay import DataReplay
from atpy.data.iqfeed.iqfeed_history_provider import *


class TestDataReplay(unittest.TestCase):
    """
    Test Data Replay
    """

    def test_basic(self):
        batch_len = 1000

        l1, l2 = list(), list()
        with IQFeedHistoryProvider() as provider, DataReplay().add_source(iter(l1), 'e1').add_source(iter(l2), 'e2') as dr:
            q = queue.Queue()
            provider.request_data_by_filters([BarsFilter(ticker="IBM", interval_len=60, interval_type='s', max_bars=batch_len),
                                              BarsFilter(ticker="AAPL", interval_len=60, interval_type='s', max_bars=batch_len)],
                                             q)

            l1.append(q.get()[1])
            l2.append(q.get()[1])

            timestamps = set()
            for i, r in enumerate(dr):
                for e in r:
                    t = r[e]['timestamp']

                if len(timestamps) > 0:
                    self.assertGreater(t, max(timestamps))

                timestamps.add(t)

                self.assertTrue(isinstance(r, dict))
                self.assertGreaterEqual(len(r), 1)

            self.assertGreaterEqual(len(timestamps), batch_len)

    def test_basic_async(self):
        batch_len = 1000

        q1, q2 = queue.Queue(), queue.Queue()
        with IQFeedHistoryProvider() as provider, DataReplay().add_source(q1.get, 'e1', True).add_source(q2.get, 'e2', True) as dr:
            q = queue.Queue()
            provider.request_data_by_filters([BarsFilter(ticker="IBM", interval_len=60, interval_type='s', max_bars=batch_len),
                                              BarsFilter(ticker="AAPL", interval_len=60, interval_type='s', max_bars=batch_len)],
                                             q)

            q1.put(q.get()[1])
            q1.put(None)
            q2.put(q.get()[1])
            q2.put(None)

            timestamps = set()
            for i, r in enumerate(dr):
                for e in r:
                    t = r[e]['timestamp']

                if len(timestamps) > 0:
                    self.assertGreater(t, max(timestamps))

                timestamps.add(t)

                self.assertTrue(isinstance(r, dict))
                self.assertGreaterEqual(len(r), 1)

            self.assertGreaterEqual(len(timestamps), batch_len)

    def test_2(self):
        l1, l2 = list(), list()
        with IQFeedHistoryProvider(num_connections=1) as provider, DataReplay().add_source(iter(l1), 'e1').add_source(iter(l2), 'e2') as dr:
            year = datetime.datetime.now().year - 1

            q1 = queue.Queue()
            provider.request_data_by_filters([BarsInPeriodFilter(ticker="AAPL", bgn_prd=datetime.datetime(year, 3, 1), end_prd=datetime.datetime(year, 4, 1), interval_len=3600, ascend=True, interval_type='s'),
                                              BarsInPeriodFilter(ticker="AAPL", bgn_prd=datetime.datetime(year, 4, 2), end_prd=datetime.datetime(year, 5, 1), interval_len=3600, ascend=True, interval_type='s'),
                                              BarsInPeriodFilter(ticker="AAPL", bgn_prd=datetime.datetime(year, 5, 2), end_prd=datetime.datetime(year, 6, 1), interval_len=3600, ascend=True, interval_type='s'),
                                              BarsInPeriodFilter(ticker="AAPL", bgn_prd=datetime.datetime(year, 8, 2), end_prd=datetime.datetime(year, 9, 1), interval_len=3600, ascend=True, interval_type='s')],
                                             q1)

            q2 = queue.Queue()
            provider.request_data_by_filters([BarsInPeriodFilter(ticker="IBM", bgn_prd=datetime.datetime(year, 4, 1), end_prd=datetime.datetime(year, 5, 1), interval_len=3600, ascend=True, interval_type='s'),
                                              BarsInPeriodFilter(ticker="IBM", bgn_prd=datetime.datetime(year, 5, 2), end_prd=datetime.datetime(year, 6, 1), interval_len=3600, ascend=True, interval_type='s'),
                                              BarsInPeriodFilter(ticker="IBM", bgn_prd=datetime.datetime(year, 6, 2), end_prd=datetime.datetime(year, 7, 1), interval_len=3600, ascend=True, interval_type='s')],
                                             q2)

            l1.append(q1.get()[1])
            l1.append(q1.get()[1])
            l1.append(q1.get()[1])
            l1.append(q1.get()[1])

            l2.append(q2.get()[1])
            l2.append(q2.get()[1])
            l2.append(q2.get()[1])

            maxl = max(max([len(l) for l in l1]), max([len(l) for l in l2]))
            timestamps = set()
            for i, r in enumerate(dr):
                for e in r:
                    t = r[e]['timestamp']

                if len(timestamps) > 0:
                    self.assertGreater(t, max(timestamps))

                timestamps.add(t)

                self.assertTrue(isinstance(r, dict))
                self.assertGreaterEqual(len(r), 1)

            self.assertGreater(maxl, 0)
            self.assertGreaterEqual(len(timestamps), maxl)

            months = set()
            for t in timestamps:
                months.add(t.month)

            self.assertTrue({3, 4, 5, 6, 8} < months)

    def test_2_async(self):
        q1, q2 = queue.Queue(), queue.Queue()
        with IQFeedHistoryProvider(num_connections=1) as provider, DataReplay().add_source(q1.get, 'e1', True).add_source(q2.get, 'e2', True) as dr:
            year = datetime.datetime.now().year - 1

            q1_history = queue.Queue()
            provider.request_data_by_filters([BarsInPeriodFilter(ticker="AAPL", bgn_prd=datetime.datetime(year, 3, 1), end_prd=datetime.datetime(year, 4, 1), interval_len=3600, ascend=True, interval_type='s'),
                                              BarsInPeriodFilter(ticker="AAPL", bgn_prd=datetime.datetime(year, 4, 2), end_prd=datetime.datetime(year, 5, 1), interval_len=3600, ascend=True, interval_type='s'),
                                              BarsInPeriodFilter(ticker="AAPL", bgn_prd=datetime.datetime(year, 5, 2), end_prd=datetime.datetime(year, 6, 1), interval_len=3600, ascend=True, interval_type='s'),
                                              BarsInPeriodFilter(ticker="AAPL", bgn_prd=datetime.datetime(year, 8, 2), end_prd=datetime.datetime(year, 9, 1), interval_len=3600, ascend=True, interval_type='s')],
                                             q1_history)

            q2_history = queue.Queue()
            provider.request_data_by_filters([BarsInPeriodFilter(ticker="IBM", bgn_prd=datetime.datetime(year, 4, 1), end_prd=datetime.datetime(year, 5, 1), interval_len=3600, ascend=True, interval_type='s'),
                                              BarsInPeriodFilter(ticker="IBM", bgn_prd=datetime.datetime(year, 5, 2), end_prd=datetime.datetime(year, 6, 1), interval_len=3600, ascend=True, interval_type='s'),
                                              BarsInPeriodFilter(ticker="IBM", bgn_prd=datetime.datetime(year, 6, 2), end_prd=datetime.datetime(year, 7, 1), interval_len=3600, ascend=True, interval_type='s')],
                                             q2_history)

            q1.put(q1_history.get()[1])
            q1.put(q1_history.get()[1])
            q1.put(q1_history.get()[1])
            q1.put(q1_history.get()[1])
            q1.put(None)

            q2.put(q2_history.get()[1])
            q2.put(q2_history.get()[1])
            q2.put(q2_history.get()[1])
            q2.put(None)

            timestamps = set()
            for i, r in enumerate(dr):
                for e in r:
                    t = r[e]['timestamp']

                if len(timestamps) > 0:
                    self.assertGreater(t, max(timestamps))

                timestamps.add(t)

                self.assertTrue(isinstance(r, dict))
                self.assertGreaterEqual(len(r), 1)

            self.assertGreaterEqual(len(timestamps), 1)

            months = set()
            for t in timestamps:
                months.add(t.month)

            self.assertTrue({3, 4, 5, 6, 8} < months)

    def test_3_performance(self):
        logging.basicConfig(level=logging.DEBUG)

        batch_len = 1000
        batch_width = 5

        l1, l2 = list(), list()
        with IQFeedHistoryProvider() as provider, DataReplay().add_source(iter(l1), 'e1').add_source(iter(l2), 'e2') as dr:
            now = datetime.datetime.now()

            q = queue.Queue()
            provider.request_data_by_filters([BarsFilter(ticker="AAPL", interval_len=60, interval_type='s', max_bars=batch_len),
                                              BarsFilter(ticker="IBM", interval_len=60, interval_type='s', max_bars=batch_len)],
                                             q)

            df1 = q.get()[1]
            dfs1 = {'AAPL': df1}
            for i in range(batch_width):
                dfs1['AAPL_' + str(i)] = df1.sample(random.randint(int(len(df1) / 3), len(df1) - 1))

            dfs1 = pd.concat(dfs1)
            l1.append(dfs1)

            df2 = q.get()[1]
            dfs2 = {'IBM': df2}
            for i in range(batch_width):
                dfs2['IBM_' + str(i)] = df2.sample(random.randint(int(len(df2) / 3), len(df2) - 1))

            dfs2 = pd.concat(dfs2)
            l2.append(dfs2)

            logging.getLogger(__name__).debug('Random data generated in ' + str(datetime.datetime.now() - now) + ' with shapes ' + str(dfs1.shape) + ', ' + str(dfs2.shape))

            prev_t = None
            now = datetime.datetime.now()

            for i, r in enumerate(dr):
                if i % 1000 == 0 and i > 0:
                    new_now = datetime.datetime.now()
                    elapsed = new_now - now
                    logging.getLogger(__name__).debug('Time elapsed ' + str(elapsed) + ' for ' + str(i) + ' iterations; ' + str(elapsed / 1000) + ' per iteration')
                    now = new_now

                for e in r:
                    t = r[e]['timestamp'][0]

                if prev_t is not None:
                    self.assertGreater(t, prev_t)

                prev_t = t

                self.assertTrue(isinstance(r, dict))
                self.assertGreaterEqual(len(r), 1)

            elapsed = datetime.datetime.now() - now
            logging.getLogger(__name__).debug('Time elapsed ' + str(elapsed) + ' for ' + str(i + 1) + ' iterations; ' + str(elapsed / (i % 1000)) + ' per iteration')

            self.assertIsNotNone(t)
            self.assertIsNotNone(prev_t)


if __name__ == '__main__':
    unittest.main()