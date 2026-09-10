"""Constants for shareholder structure tables."""

# Shareholder count per report period (stk_holdernumber)
TUSHARE_HOLDER_NUMBER_FIELDS = [
    "ts_code",
    "ann_date",
    "end_date",
    "holder_num",
]

HOLDER_NUMBER_COLUMNS = [
    "code",
    "announce_date",
    "report_period",
    "holder_count",
    "update_time",
]

HOLDER_NUMBER_PAGE_SIZE = 100

# Top-10 holders and top-10 float holders share one layout. hold_amount is in 股.
TUSHARE_TOP10_HOLDER_FIELDS = [
    "ts_code",
    "ann_date",
    "end_date",
    "holder_name",
    "hold_amount",
    "hold_ratio",
    "hold_float_ratio",
    "hold_change",
    "holder_type",
]

TOP10_HOLDER_COLUMNS = [
    "code",
    "announce_date",
    "report_period",
    "holder_name",
    "hold_shares",
    "hold_ratio",
    "hold_float_ratio",
    "hold_change",
    "holder_type",
    "update_time",
]

TOP10_HOLDER_PAGE_SIZE = 5000
DEFAULT_HOLDER_START_DATE = "19900101"
