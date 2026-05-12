"""Constants for daily market data and adjustment factors."""

# Provider fields are used only by Tushare adapters and raw output files.
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

# Local daily tables keep provider-neutral field names and local units.
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

# Adjustment factors stay in a separate table so adjusted prices can be rebuilt.
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

# Tushare returns volume in lots and amount in thousand yuan.
TUSHARE_VOLUME_TO_LOCAL = 100
TUSHARE_AMOUNT_TO_LOCAL = 1000
