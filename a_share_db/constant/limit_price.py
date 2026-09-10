"""Constants for daily limit-up/limit-down price data."""

# Provider fields are used only by the Tushare adapter and optional raw files.
TUSHARE_LIMIT_PRICE_FIELDS = [
    "ts_code",
    "trade_date",
    "up_limit",
    "down_limit",
]

# Local rows keep the price bounds that make A-share fills realistic in backtests.
LIMIT_PRICE_COLUMNS = [
    "code",
    "trade_date",
    "limit_up_price",
    "limit_down_price",
    "update_time",
]

# Tushare stk_limit history starts in 2007 and caps each page well above 4000 rows.
DEFAULT_LIMIT_PRICE_START_DATE = "20070101"
LIMIT_PRICE_PAGE_SIZE = 4000
