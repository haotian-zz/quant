"""Constants for daily basic indicator data."""

# Provider fields are used only by the Tushare adapter and optional raw files.
TUSHARE_DAILY_BASIC_FIELDS = [
    "ts_code",
    "trade_date",
    "close",
    "turnover_rate",
    "turnover_rate_f",
    "volume_ratio",
    "pe",
    "pe_ttm",
    "pb",
    "ps",
    "ps_ttm",
    "dv_ratio",
    "dv_ttm",
    "total_share",
    "float_share",
    "free_share",
    "total_mv",
    "circ_mv",
]

# Local daily basic rows use provider-neutral field names and local units.
DAILY_BASIC_COLUMNS = [
    "code",
    "trade_date",
    "close",
    "turnover_rate",
    "turnover_rate_free_float",
    "volume_ratio",
    "pe",
    "pe_ttm",
    "pb",
    "ps",
    "ps_ttm",
    "dividend_yield",
    "dividend_yield_ttm",
    "total_shares",
    "float_shares",
    "free_float_shares",
    "total_market_value",
    "float_market_value",
    "update_time",
]

# Tushare returns share counts in 10k shares and market values in 10k yuan.
TUSHARE_SHARE_TO_LOCAL = 10000
TUSHARE_MARKET_VALUE_TO_LOCAL = 10000

# Tushare daily_basic returns at most 6000 rows per request. An 18-year calendar
# window stays below that for one stock while keeping request count reasonable.
DAILY_BASIC_WINDOW_CALENDAR_DAYS = 365 * 18
