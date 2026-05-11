"""Constants for daily market data and adjustment factors."""

TUSHARE_DAILY_FIELDS = [
    "ts_code",
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "pre_close",
    "change",
    "pct_chg",
    "vol",
    "amount",
]

DAILY_PRICE_COLUMNS = [
    "code",
    "name",
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "pre_close",
    "change",
    "pct_chg",
    "volume",
    "amount",
    "adjust_type",
    "update_time",
]

TUSHARE_ADJ_FACTOR_FIELDS = [
    "ts_code",
    "trade_date",
    "adj_factor",
]

ADJ_FACTOR_COLUMNS = [
    "code",
    "trade_date",
    "adjust_factor",
    "update_time",
]

ADJUST_TYPES = ["none", "qfq", "hfq"]

TUSHARE_VOLUME_TO_LOCAL = 100
TUSHARE_AMOUNT_TO_LOCAL = 1000
