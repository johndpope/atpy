import logging
import threading
import typing

import pandas as pd

import atpy.portfolio.order as orders


class MockBroker(object):
    """
    Mock broker for executing trades based on the current streaming prices. Works with realtime and historical data.
    """

    def __init__(self, listeners, accept_bars: typing.Callable = None, accept_ticks: typing.Callable = None):
        """
        Add source for data generation
        :param listeners: listeners
        :param accept_bars: treat event like bar data. Has to return the bar dataframe. If None, then the event is not accepted
        :param accept_ticks: treat event like tick data. Has to return the tick dataframe. If None, then the event is not accepted
        """

        if accept_bars is not None:
            self.accept_bars = accept_bars
        else:
            self.accept_bars = lambda e: e['data'] if e['type'] == 'bar' else None

        if accept_ticks is not None:
            self.accept_ticks = accept_ticks
        else:
            self.accept_ticks = lambda e: e['data'] if e['type'] == 'level_1_tick' else None

        self.listeners = listeners
        self.listeners += self.on_event

        self._pending_orders = list()
        self._lock = threading.RLock()

    def process_order_request(self, order):
        with self._lock:
            self._pending_orders.append(order)

    def on_event(self, event):
        if event['type'] == 'order_request':
            self.process_order_request(event['data'])
        elif self.accept_ticks(event) is not None:
            self.process_tick_data(self.accept_ticks(event))
        elif self.accept_bars(event) is not None:
            self.process_bar_data(self.accept_bars(event))

    def process_tick_data(self, data):
        with self._lock:
            matching_orders = [o for o in self._pending_orders if o.symbol == data['symbol']]
            for o in matching_orders:
                if o.order_type == orders.Type.BUY:
                    if 'tick_id' in data:
                        o.add_position(data['last_size'], data['ask'])
                    else:
                        o.add_position(data['ask_size'] if data['ask_size'] > 0 else data['most_recent_trade_size'], data['ask'] if data['ask_size'] > 0 else data['most_recent_trade'])
                elif o.order_type == orders.Type.SELL:
                    if 'tick_id' in data:
                        o.add_position(data['last_size'], data['bid'])
                    else:
                        o.add_position(data['bid_size'] if data['bid_size'] > 0 else data['most_recent_trade_size'], data['bid'] if data['bid_size'] > 0 else data['most_recent_trade'])

                if o.fulfill_time is not None:
                    self._pending_orders.remove(o)

                    logging.getLogger(__name__).info("Order fulfilled: " + str(o))

                    self.listeners({'type': 'order_fulfilled', 'data': o})

    def process_bar_data(self, data):
        with self._lock:
            for o, slc in [(o, data.loc[pd.IndexSlice[:, o.symbol], :]) for o in self._pending_orders]:
                if not slc.empty:
                    o.add_position(slc.iloc[-1]['period_volume'], slc.iloc[-1]['close'])

                    if o.fulfill_time is not None:
                        self._pending_orders.remove(o)

                        logging.getLogger(__name__).info("Order fulfilled: " + str(o))

                        self.listeners({'type': 'order_fulfilled', 'data': o})
