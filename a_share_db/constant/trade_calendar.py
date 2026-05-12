"""Constants for trade calendar tables and provider fields."""

# Provider field names are isolated from the curated calendar schema.
TUSHARE_TRADE_CALENDAR_FIELDS = [
    "exchange",
    "cal_date",
    "is_open",
    "pretrade_date",
]

# Local calendar rows use stable exchange/date fields for backtests and live jobs.
TRADE_CALENDAR_COLUMNS = [
    "exchange",
    "calendar_date",
    "is_trading_day",
    "previous_trade_date",
    "update_time",
]

# A-share stock trading normally needs SSE and SZSE calendars.
DEFAULT_A_SHARE_EXCHANGES = ["SSE", "SZSE"]

# Commodity and futures exchanges are available when explicitly requested.
ALL_TRADE_CAL_EXCHANGES = ["SSE", "SZSE", "CFFEX", "SHFE", "CZCE", "DCE", "INE"]
