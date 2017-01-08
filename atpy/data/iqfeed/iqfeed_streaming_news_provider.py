from atpy.data.iqfeed.iqfeed_base_provider import *
from pyiqfeed import *
import queue


class IQFeedStreamingNewsProvider(IQFeedBaseProvider, SilentQuoteListener):

    def __init__(self, minibatch=1, key_suffix=''):
        super().__init__(name="data provider listener")

        self.minibatch = minibatch
        self.conn = None
        self.key_suffix = key_suffix

    def __iter__(self):
        super().__iter__()

        if self.conn is None:
            self.conn = iq.QuoteConn()
            self.conn.add_listener(self)
            self.conn.connect()
            self.conn.news_on()

            self.queue = queue.Queue()

        return self

    def __enter__(self):
        super().__enter__()

        self.conn = iq.QuoteConn()
        self.conn.add_listener(self)
        self.conn.connect()
        self.conn.news_on()

        self.queue = queue.Queue()

        return self

    def __exit__(self, exception_type, exception_value, traceback):
        """Disconnect connection etc"""
        self.conn.remove_listener(self)
        self.conn.disconnect()
        self.conn = None

    def __del__(self):
        if self.conn is not None:
            self.conn.remove_listener(self)
            self.conn.disconnect()

    def __next__(self) -> map:
        result = None

        for i, datum in enumerate(iter(self.queue.get, None)):
            if result is None:
                result = {f + self.key_suffix: list() for f in datum._fields}

            for j, f in enumerate(datum._fields):
                result[f + self.key_suffix].append(datum[j])

            if (i + 1) % self.minibatch == 0:
                return result

    def __getattr__(self, name):
        if self.conn is not None:
            return getattr(self.conn, name)
        else:
            raise AttributeError

    def process_news(self, news_item: QuoteConn.NewsMsg) -> None:
        self.queue.put(news_item)