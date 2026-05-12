"""Default settings for common one-command workflows."""

# Keep wrapper command defaults in one place so daily jobs use the same limits.
DEFAULT_REQUEST_INTERVAL = 0.13
DEFAULT_PROGRESS_EVERY = 50
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_INTERVAL = 5.0

# History start dates are conservative project defaults, not provider fields.
DEFAULT_HISTORY_START_DATE = "19900101"
DEFAULT_TRADE_CALENDAR_START_DATE = "19901219"
