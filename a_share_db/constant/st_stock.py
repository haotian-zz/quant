"""Constants for the daily ST / risk-warning stock list."""

TUSHARE_ST_STOCK_FIELDS = [
    "ts_code",
    "name",
    "trade_date",
    "type",
    "type_name",
]

# Daily membership table: a stock appears on every trade date it carried a warning.
ST_STOCK_COLUMNS = [
    "code",
    "name",
    "trade_date",
    "st_type",
    "st_type_name",
    "update_time",
]

# Verified provider coverage starts in 2005; earlier ST history can be derived
# from stock_name_history when a name contains ST.
DEFAULT_ST_STOCK_START_DATE = "20050104"
