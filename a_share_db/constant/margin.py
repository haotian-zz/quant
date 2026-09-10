"""Constants for margin trading and securities lending data."""

# Per-stock detail (margin_detail). Balances/amounts are in 元, volumes in 股.
TUSHARE_MARGIN_DETAIL_FIELDS = [
    "ts_code",
    "trade_date",
    "rzye",
    "rzmre",
    "rzche",
    "rqye",
    "rqyl",
    "rqmcl",
    "rqchl",
    "rzrqye",
]

TUSHARE_MARGIN_DETAIL_FIELD_MAP = {
    "rzye": "financing_balance",
    "rzmre": "financing_buy_amount",
    "rzche": "financing_repay_amount",
    "rqye": "lending_balance",
    "rqyl": "lending_volume",
    "rqmcl": "lending_sell_volume",
    "rqchl": "lending_repay_volume",
    "rzrqye": "margin_balance",
}

MARGIN_COLUMNS = ["code", "trade_date"] + list(TUSHARE_MARGIN_DETAIL_FIELD_MAP.values()) + ["update_time"]

DEFAULT_MARGIN_START_DATE = "20100331"
MARGIN_PAGE_SIZE = 4000

# Exchange-level summary (margin). Same units as the detail table.
TUSHARE_MARGIN_SUMMARY_FIELDS = [
    "trade_date",
    "exchange_id",
    "rzye",
    "rzmre",
    "rzche",
    "rqye",
    "rqyl",
    "rqmcl",
    "rzrqye",
]

TUSHARE_MARGIN_SUMMARY_FIELD_MAP = {
    "rzye": "financing_balance",
    "rzmre": "financing_buy_amount",
    "rzche": "financing_repay_amount",
    "rqye": "lending_balance",
    "rqyl": "lending_volume",
    "rqmcl": "lending_sell_volume",
    "rzrqye": "margin_balance",
}

MARGIN_SUMMARY_COLUMNS = ["exchange", "trade_date"] + list(TUSHARE_MARGIN_SUMMARY_FIELD_MAP.values()) + ["update_time"]

MARGIN_SUMMARY_EXCHANGES = ["SSE", "SZSE", "BSE"]
