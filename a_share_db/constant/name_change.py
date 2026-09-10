"""Constants for the stock name history table."""

TUSHARE_NAME_CHANGE_FIELDS = [
    "ts_code",
    "name",
    "start_date",
    "end_date",
    "ann_date",
    "change_reason",
]

# Each row is one name validity interval; end_date is blank for the current name.
STOCK_NAME_HISTORY_COLUMNS = [
    "code",
    "name",
    "start_date",
    "end_date",
    "announce_date",
    "change_reason",
    "update_time",
]

# The full-market namechange query returns about 14k rows across two pages.
NAME_CHANGE_PAGE_SIZE = 10000
