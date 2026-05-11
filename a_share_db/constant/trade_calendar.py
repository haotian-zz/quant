"""Constants for trade calendar tables and provider fields."""

TUSHARE_TRADE_CALENDAR_FIELDS = [
    "exchange",
    "cal_date",
    "is_open",
    "pretrade_date",
]

TRADE_CALENDAR_COLUMNS = [
    "exchange",
    "calendar_date",
    "is_trading_day",
    "previous_trade_date",
    "update_time",
]

DEFAULT_A_SHARE_EXCHANGES = ["SSE", "SZSE"]
ALL_TRADE_CAL_EXCHANGES = ["SSE", "SZSE", "CFFEX", "SHFE", "CZCE", "DCE", "INE"]
