"""Constants for convertible bond tables. Bond codes keep the Wind-style suffix (113008.SH)."""

TUSHARE_CB_BASIC_FIELD_MAP = {
    "ts_code": "bond_code",
    "bond_full_name": "bond_full_name",
    "bond_short_name": "bond_short_name",
    "cb_type": "bond_type",
    "cb_code": "bond_symbol",
    "stk_code": "code",
    "stk_short_name": "stock_name",
    "maturity": "maturity_years",
    "par": "par_value",
    "issue_price": "issue_price",
    "issue_size": "issue_size",
    "remain_size": "remaining_size",
    "value_date": "value_date",
    "maturity_date": "maturity_date",
    "rate_type": "rate_type",
    "coupon_rate": "coupon_rate",
    "add_rate": "compensation_rate",
    "pay_per_year": "payments_per_year",
    "list_date": "list_date",
    "delist_date": "delist_date",
    "exchange": "exchange",
    "conv_start_date": "conversion_start_date",
    "conv_end_date": "conversion_end_date",
    "conv_stop_date": "conversion_stop_date",
    "first_conv_price": "initial_conversion_price",
    "conv_price": "conversion_price",
    "rate_clause": "rate_clause",
}
CONVERTIBLE_BOND_BASIC_COLUMNS = list(TUSHARE_CB_BASIC_FIELD_MAP.values()) + ["update_time"]
CB_BASIC_PAGE_SIZE = 2000

# cb_daily: vol in 手, amount 万元 -> 元.
TUSHARE_CB_DAILY_FIELD_MAP = {
    "ts_code": "bond_code",
    "trade_date": "trade_date",
    "pre_close": "pre_close",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "change": "change",
    "pct_chg": "pct_chg",
    "vol": "volume",
    "amount": "amount",
}
CONVERTIBLE_BOND_DAILY_COLUMNS = list(TUSHARE_CB_DAILY_FIELD_MAP.values()) + ["update_time"]
CB_DAILY_SCALES = {"amount": 10000}
DEFAULT_CB_DAILY_START_DATE = "20100104"
