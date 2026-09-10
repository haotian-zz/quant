"""Constants for daily suspension and resumption records."""

TUSHARE_SUSPEND_FIELDS = [
    "ts_code",
    "trade_date",
    "suspend_timing",
    "suspend_type",
]

# One row per stock per trade date that had a suspend or resume event.
SUSPEND_COLUMNS = [
    "code",
    "trade_date",
    "suspend_timing",
    "suspend_type",
    "update_time",
]

# Provider codes are S (suspend) and R (resume); local values are descriptive.
TUSHARE_SUSPEND_TYPE_MAP = {
    "S": "suspend",
    "R": "resume",
}

# Tushare suspend_d by stock is truncated, so the table is built by trade date.
DEFAULT_SUSPEND_START_DATE = "19990528"
