import collections
import datetime

import atpy.data.iqfeed.util as iqfeedutil
import pyevents.events as events
from atpy.data.iqfeed.filters import *
from atpy.data.iqfeed.util import *


class TicksFilter(NamedTuple):
    """
    Ticks filter parameters
    """

    ticker: str
    max_ticks: int
    ascend: bool
    timeout: int

TicksFilter.__new__.__defaults__ = (False, None)


class TicksForDaysFilter(NamedTuple):
    """
    Ticks for days filter parameters
    """

    ticker: str
    num_days: int
    bgn_flt: datetime.time
    end_flt: datetime.time
    ascend: bool
    max_ticks: int
    timeout: int

TicksForDaysFilter.__new__.__defaults__ = (None, None, False, None, None)


class TicksInPeriodFilter(NamedTuple):
    """
    Ticks in period filter parameters
    """

    ticker: str
    bgn_prd: datetime.datetime
    end_prd: datetime.datetime
    bgn_flt: datetime.time
    end_flt: datetime.time
    ascend: bool
    max_ticks: int
    timeout: int

TicksInPeriodFilter.__new__.__defaults__ = (None, None, False, None, None)


class BarsFilter(NamedTuple):
    """
    Bars filter parameters
    """

    ticker: str
    interval_len: int
    interval_type: str
    max_bars: int
    ascend: bool
    timeout: int

BarsFilter.__new__.__defaults__ = (False, None)


class BarsForDaysFilter(NamedTuple):
    """
    Bars for days filter parameters
    """

    ticker: str
    interval_len: int
    interval_type: str
    days: int
    num_days: int
    bgn_flt: datetime.time
    end_flt: datetime.time
    ascend: bool
    max_bars: int
    timeout: int

BarsForDaysFilter.__new__.__defaults__ = (None, None, False, None, None)


class BarsInPeriodFilter(NamedTuple):
    """
    Bars in period filter parameters
    """

    ticker: str
    interval_len: int
    interval_type: str
    bgn_prd: datetime.datetime
    end_prd: datetime.datetime
    bgn_flt: datetime.time
    end_flt: datetime.time
    ascend: bool
    max_ticks: int
    timeout: int

TicksInPeriodFilter.__new__.__defaults__ = (None, None, False, None, None)


class BarsDailyFilter(NamedTuple):
    """
    Daily bars filter parameters
    """

    ticker: str
    num_days: int
    ascend: bool = False
    timeout: int = None

BarsDailyFilter.__new__.__defaults__ = (False, None)


class BarsDailyForDatesFilter(NamedTuple):
    """
    Daily bars for dates filter parameters
    """

    ticker: str
    bgn_dt: datetime.date
    end_dt: datetime.date
    ascend: bool = False
    max_days: int = None
    timeout: int = None

BarsDailyForDatesFilter.__new__.__defaults__ = (False, None, None)


class BarsWeeklyFilter(NamedTuple):
    """
    Weekly bars filter parameters
    """

    ticker: str
    num_weeks: int
    ascend: bool
    timeout: int

BarsWeeklyFilter.__new__.__defaults__ = (False, None)


class BarsMonthlyFilter(NamedTuple):
    """
    Monthly bars filter parameters
    """

    ticker: str
    num_months: int
    ascend: bool
    timeout: int

BarsMonthlyFilter.__new__.__defaults__ = (False, None)


class IQFeedHistoryListener(object, metaclass=events.GlobalRegister):
    """
    IQFeed historical data listener. See the unit test on how to use
    """

    def __init__(self, minibatch=None, fire_batches=False, fire_ticks=False, column_mode=True, key_suffix='', filter_provider=DefaultFilterProvider()):
        """
        :param minibatch: size of the minibatch
        :param fire_batches: raise event for each batch
        :param fire_ticks: raise event for each tick
        :param column_mode: whether to organize the data in columns or rows
        :param key_suffix: suffix for field names
        :param filter_provider: news filter list
        """
        self.minibatch = minibatch
        self.fire_batches = fire_batches
        self.fire_ticks = fire_ticks
        self.column_mode = column_mode
        self.key_suffix = key_suffix
        self.current_minibatch = list()
        self.current_filter = None
        self.filter_provider = filter_provider
        self.conn = None

    def __enter__(self):
        iqfeedutil.launch_service()
        self.conn = iq.HistoryConn()
        self.conn.connect()
        self.is_running = True
        self.producer_thread = threading.Thread(target=self.produce, daemon=True)
        self.producer_thread.start()

        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.conn.disconnect()
        self.conn = None
        self.is_running = False

    def __del__(self):
        if self.conn is not None:
            self.conn.disconnect()
            self.cfg = None

    def __getattr__(self, name):
        if self.conn is not None:
            return getattr(self.conn, name)
        else:
            raise AttributeError

    def produce(self):
        for f in self.filter_provider:
            self.current_filter = f

            if isinstance(f, TicksFilter):
                method = self.conn.request_ticks
            elif isinstance(f, TicksForDaysFilter):
                method = self.conn.request_ticks_for_days
            elif isinstance(f, TicksInPeriodFilter):
                method = self.conn.request_ticks_in_period
            elif isinstance(f, BarsFilter):
                method = self.conn.request_bars
            elif isinstance(f, BarsForDaysFilter):
                method = self.conn.request_bars_for_days
            elif isinstance(f, BarsInPeriodFilter):
                method = self.conn.request_bars_in_period
            elif isinstance(f, BarsDailyFilter):
                method = self.conn.request_daily_data
            elif isinstance(f, BarsDailyForDatesFilter):
                method = self.conn.request_daily_data_for_dates
            elif isinstance(f, BarsWeeklyFilter):
                method = self.conn.request_weekly_data
            elif isinstance(f, BarsMonthlyFilter):
                method = self.conn.request_monthly_data

            data = method(*f)

            processed_data = list()

            for datum in data:
                datum = datum[0] if len(datum) == 1 else datum

                if self.fire_ticks:
                    self.process_datum(self._process_data(iqfeedutil.iqfeed_to_dict(datum, self.key_suffix)))

                processed_data.append(datum)

                if self.minibatch is not None:
                    self.current_minibatch.append(datum)

                    if len(self.current_minibatch) == self.minibatch:
                        mb_data = self._process_data(iqfeedutil.create_batch(self.current_minibatch, self.column_mode, self.key_suffix))
                        self.process_minibatch(mb_data)
                        self.current_minibatch = list()

            if self.fire_batches:
                batch_data = self._process_data(iqfeedutil.create_batch(processed_data, self.column_mode, self.key_suffix))
                self.process_batch(batch_data)

            if not self.is_running:
                return

    def _process_data(self, data):
        if isinstance(self.current_filter, TicksFilter) or isinstance(self.current_filter, TicksForDaysFilter) or isinstance(self.current_filter, TicksInPeriodFilter):
            return self._process_ticks_data(data)
        elif isinstance(self.current_filter, BarsFilter) or isinstance(self.current_filter, BarsForDaysFilter) or isinstance(self.current_filter, BarsInPeriodFilter):
            return self._process_bars_data(data)
        elif isinstance(self.current_filter, BarsDailyFilter) or isinstance(self.current_filter, BarsDailyForDatesFilter) or isinstance(self.current_filter, BarsWeeklyFilter) or isinstance(self.current_filter, BarsMonthlyFilter):
            return self._process_daily_data(data)

    def _process_ticks_data(self, data):
        if isinstance(data, dict):
            result = dict()

            result['Date'] = data.pop('date')
            result['Time'] = data.pop('time')
            result['Last'] = data.pop('last')
            result['Last Size'] = data.pop('last_sz')
            result['Total Volume'] = data.pop('tot_vlm')
            result['Bid'] = data.pop('bid')
            result['Ask'] = data.pop('ask')
            result['TickID'] = data.pop('tick_id')
            result['Basis For Last'] = data.pop('last_type')
            result['Trade Market Center'] = data.pop('mkt_ctr')
            result['cond1'] = data.pop('cond1')
            result['cond2'] = data.pop('cond2')
            result['cond3'] = data.pop('cond3')
            result['cond4'] = data.pop('cond4')

            if isinstance(result['Date'], collections.Iterable):
                result['Symbol'] = [self.current_filter.ticker] * len(result['Date'])
            else:
                result['Symbol'] = self.current_filter.ticker
        elif isinstance(data, collections.Iterable):
            result = list()
            for d in data:
                result.append(self._process_ticks_data(d))

        return result

    def _process_bars_data(self, data):
        if isinstance(data, dict):
            result = dict()

            result['Date'] = data.pop('date')
            result['Time'] = data.pop('time')
            result['High'] = data.pop('high_p')
            result['Low'] = data.pop('low_p')
            result['Open'] = data.pop('open_p')
            result['Close'] = data.pop('close_p')
            result['Total Volume'] = data.pop('tot_vlm')
            result['Period Volume'] = data.pop('prd_vlm')
            result['Number of Trades'] = data.pop('num_trds')

            if isinstance(result['Date'], collections.Iterable):
                result['Symbol'] = [self.current_filter.ticker] * len(result['Date'])
            else:
                result['Symbol'] = self.current_filter.ticker
        elif isinstance(data, collections.Iterable):
            result = list()
            for d in data:
                result.append(self._process_bars_data(d))

        return result

    def _process_daily_data(self, data):
        if isinstance(data, dict):
            result = dict()

            result['Date'] = data.pop('date')
            result['High'] = data.pop('high_p')
            result['Low'] = data.pop('low_p')
            result['Open'] = data.pop('open_p')
            result['Close'] = data.pop('close_p')
            result['Period Volume'] = data.pop('prd_vlm')
            result['Open Interest'] = data.pop('open_int')

            if isinstance(result['Date'], collections.Iterable):
                result['Symbol'] = [self.current_filter.ticker] * len(result['Date'])
            else:
                result['Symbol'] = self.current_filter.ticker
        elif isinstance(data, collections.Iterable):
            result = list()
            for d in data:
                result.append(self._process_daily_data(d))

        return result

    @events.after
    def process_datum(self, data):
        return {'type': 'level_1_tick', 'data': data}

    @events.after
    def process_batch(self, data):
        return {'type': 'level_1_tick_batch', 'data': data}

    def batch_provider(self):
        return IQFeedDataProvider(self.process_batch)

    @events.after
    def process_minibatch(self, data):
        return {'type': 'level_1_tick_mb', 'data': data}

    def minibatch_provider(self):
        return IQFeedDataProvider(self.process_minibatch)
