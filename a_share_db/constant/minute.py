"""Constants for historical minute market data."""

# Provider fields are used only by the Tushare minute adapter and raw files.
TUSHARE_MINUTE_FIELDS = [
    "ts_code",
    "trade_time",
    "open",
    "close",
    "high",
    "low",
    "vol",
    "amount",
]

# Local minute bars use provider-neutral names and local units.
MINUTE_BAR_COLUMNS = [
    "code",
    "name",
    "trade_date",
    "bar_end_time",
    "frequency",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "adjust_type",
    "update_time",
]

# Local frequency names are short and independent from provider parameters.
MINUTE_FREQUENCIES = ["1m", "5m", "15m", "30m", "60m"]

TUSHARE_MINUTE_FREQ_MAP = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "60m": "60min",
}

TUSHARE_MINUTE_FREQ_REVERSE_MAP = {
    provider_freq: local_freq
    for local_freq, provider_freq in TUSHARE_MINUTE_FREQ_MAP.items()
}

TUSHARE_MINUTE_MAX_ROWS = 8000

# Use safe upper estimates so each request stays below the provider row cap.
MINUTE_MAX_BARS_PER_TRADING_DAY = {
    "1m": 242,
    "5m": 49,
    "15m": 17,
    "30m": 9,
    "60m": 5,
}

# Max trading days per request, using a strict less-than-8000 limit.
DEFAULT_MINUTE_WINDOW_TRADING_DAYS = {
    frequency: (TUSHARE_MINUTE_MAX_ROWS - 1) // bars_per_day
    for frequency, bars_per_day in MINUTE_MAX_BARS_PER_TRADING_DAY.items()
}
