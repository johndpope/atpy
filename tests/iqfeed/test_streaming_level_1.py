import unittest

from atpy.data.iqfeed.iqfeed_level_1_provider import *


class TestIQFeedLevel1(unittest.TestCase):
    """
    IQFeed streaming news test, which checks whether the class works in basic terms
    """

    def test_fundamentals(self):
        with IQFeedLevel1Listener(minibatch=2) as listener, listener.fundamentals_provider() as provider:
            listener.watch('IBM')
            listener.watch('AAPL')
            listener.watch('GOOG')
            listener.watch('MSFT')
            listener.watch('SPY')
            listener.request_watches()
            e1 = threading.Event()

            def on_fund_item(event):
                try:
                    self.assertEqual(len(event['data']), 50)
                finally:
                    e1.set()

            listener.on_fundamentals += on_fund_item

            e1.wait()

            for i, fund_item in enumerate(provider):
                self.assertEqual(len(fund_item), 50)
                s = fund_item['symbol']
                self.assertTrue('SPY' == s or 'AAPL' == s or 'IBM' == s or 'GOOG' == s or 'MSFT' == s)

                if i == 1:
                    break

    def test_get_fundamentals(self):
        with IQFeedLevel1Listener(fire_ticks=False) as listener, listener.fundamentals_provider():
            funds = listener.get_fundamentals({'IBM', 'AAPL', 'GOOG', 'MSFT'})
            self.assertTrue('AAPL' in funds and 'IBM' in funds and 'GOOG' in funds and 'MSFT' in funds)
            for _, v in funds.items():
                self.assertGreater(len(v), 0)

    def test_summary(self):
        with IQFeedLevel1Listener(minibatch=2) as listener, listener.summary_provider() as data_provider:
            listener.watch('IBM')
            listener.watch('AAPL')
            listener.watch('GOOG')
            listener.watch('MSFT')
            listener.watch('SPY')

            e1 = threading.Event()

            def on_summary_item(event):
                try:
                    self.assertEqual(len(event['data']), 16)
                finally:
                    e1.set()

            listener.on_summary += on_summary_item

            e1.wait()

            for i, summary_item in enumerate(data_provider):
                self.assertEqual(len(summary_item), 16)
                s = summary_item['symbol']
                self.assertTrue('SPY' == s or 'AAPL' == s or 'IBM' == s or 'GOOG' == s or 'MSFT' == s)

                if i == 1:
                    break

    def test_update(self):
        with IQFeedLevel1Listener(minibatch=2) as listener, listener.update_provider() as update_provider:
            listener.watch('IBM')
            listener.watch('AAPL')
            listener.watch('GOOG')
            listener.watch('MSFT')
            listener.watch('SPY')

            e1 = threading.Event()

            def on_update_item(event):
                try:
                    self.assertEqual(len(event['data']), 16)
                finally:
                    e1.set()

            listener.on_update += on_update_item

            e2 = threading.Event()

            def on_update_mb(event):
                try:
                    update_item = event['data']
                    self.assertEqual(update_item.shape, (2, 16))
                    l = list(update_item['symbol'])
                    self.assertTrue('SPY' in l or 'AAPL' in l or 'IBM' in l or 'GOOG' in l or 'MSFT' in l)
                finally:
                    e2.set()

            listener.on_update_mb += on_update_mb

            e1.wait()
            e2.wait()

            for i, update_item in enumerate(update_provider):
                self.assertEqual(update_item.shape, (2, 16))
                l = list(update_item['symbol'])
                self.assertTrue('SPY' in l or 'AAPL' in l or 'IBM' in l or 'GOOG' in l or 'MSFT' in l)

                if i == 1:
                    break

    def test_news(self):
        with IQFeedLevel1Listener(minibatch=2) as listener, listener.news_provider() as provider:
            listener.watch('IBM')
            listener.watch('AAPL')
            listener.watch('GOOG')
            listener.watch('SPY')
            listener.news_on()

            e1 = threading.Event()

            def on_news_item(event):
                try:
                    news_item = event['data']
                    self.assertEqual(len(news_item), 6)
                    self.assertGreater(len(news_item['headline']), 0)
                finally:
                    e1.set()

            listener.on_news += on_news_item

            e1.wait()

            for i, news_item in enumerate(provider):
                self.assertEqual(len(news_item), 6)
                self.assertEqual(len(news_item['headline']), 2)
                self.assertGreater(len(news_item['headline']), 0)

                if i == 1:
                    break


if __name__ == '__main__':
    unittest.main()
