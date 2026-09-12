"""Constants for exchange-traded option tables (SSE/SZSE ETF options, CFFEX index options).

Option codes keep the Wind-style suffix (10000001.SH, IO2412-C-4000.CFX).
"""

TUSHARE_OPTION_BASIC_FIELD_MAP = {
    "ts_code": "option_code",
    "symbol": "symbol",
    "exchange": "exchange",
    "name": "name",
    "per_unit": "contract_unit",
    "opt_code": "product_code",
    "opt_type": "option_type",
    "call_put": "call_put",
    "exercise_type": "exercise_type",
    "exercise_price": "strike_price",
    "opt_multiplier": "multiplier",
    "s_month": "settlement_month",
    "maturity_date": "maturity_date",
    "list_price": "list_price",
    "list_date": "list_date",
    "delist_date": "delist_date",
    "last_edate": "last_exercise_date",
    "last_ddate": "last_delivery_date",
    "quote_unit": "quote_unit",
    "min_price_chg": "min_price_change",
}
OPTION_BASIC_COLUMNS = list(TUSHARE_OPTION_BASIC_FIELD_MAP.values()) + ["update_time"]
OPTION_EXCHANGES = ["SSE", "SZSE", "CFFEX"]
OPTION_BASIC_PAGE_SIZE = 5000

# opt_daily: vol in 手, amount 万元 -> 元, oi in 手.
TUSHARE_OPTION_DAILY_FIELD_MAP = {
    "ts_code": "option_code",
    "trade_date": "trade_date",
    "exchange": "exchange",
    "pre_settle": "pre_settle",
    "pre_close": "pre_close",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "settle": "settle",
    "vol": "volume",
    "amount": "amount",
    "oi": "open_interest",
}
OPTION_DAILY_COLUMNS = list(TUSHARE_OPTION_DAILY_FIELD_MAP.values()) + ["update_time"]
OPTION_DAILY_SCALES = {"amount": 10000}
DEFAULT_OPTION_START_DATE = "20150209"
