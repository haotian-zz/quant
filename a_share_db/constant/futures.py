"""Constants for stock index futures (CFFEX) tables.

Contract identifiers keep the Wind-style code (for example IF2609.CFX, and
IF.CFX for the main continuous series), for the same reason index codes do:
the bare symbol is not unique across exchanges.
"""

# Contract master (fut_basic)
TUSHARE_FUTURES_BASIC_FIELD_MAP = {
    "ts_code": "contract_code",
    "symbol": "symbol",
    "exchange": "exchange",
    "name": "name",
    "fut_code": "product_code",
    "multiplier": "multiplier",
    "trade_unit": "trade_unit",
    "per_unit": "per_unit",
    "quote_unit": "quote_unit",
    "quote_unit_desc": "quote_unit_description",
    "d_mode_desc": "delivery_mode",
    "list_date": "list_date",
    "delist_date": "delist_date",
    "d_month": "delivery_month",
    "last_ddate": "last_delivery_date",
}
TUSHARE_FUTURES_BASIC_FIELDS = list(TUSHARE_FUTURES_BASIC_FIELD_MAP.keys())
FUTURES_BASIC_COLUMNS = list(TUSHARE_FUTURES_BASIC_FIELD_MAP.values()) + ["update_time"]

# Daily quotes (fut_daily). Prices and settlement are index points; vol in 手, amount in 万元.
TUSHARE_FUTURES_DAILY_FIELD_MAP = {
    "ts_code": "contract_code",
    "trade_date": "trade_date",
    "pre_close": "pre_close",
    "pre_settle": "pre_settle",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "settle": "settle",
    "change1": "change_vs_pre_settle",
    "change2": "change_vs_pre_close",
    "vol": "volume",
    "amount": "amount",
    "oi": "open_interest",
    "oi_chg": "open_interest_change",
}
TUSHARE_FUTURES_DAILY_FIELDS = list(TUSHARE_FUTURES_DAILY_FIELD_MAP.keys())
FUTURES_DAILY_COLUMNS = list(TUSHARE_FUTURES_DAILY_FIELD_MAP.values()) + ["update_time"]
TUSHARE_FUTURES_AMOUNT_TO_LOCAL = 10000
FUTURES_DAILY_PAGE_SIZE = 2000

# Main contract mapping (fut_mapping): which contract the continuous series points to each day.
TUSHARE_FUTURES_MAPPING_FIELD_MAP = {
    "ts_code": "continuous_code",
    "trade_date": "trade_date",
    "mapping_ts_code": "contract_code",
}
TUSHARE_FUTURES_MAPPING_FIELDS = list(TUSHARE_FUTURES_MAPPING_FIELD_MAP.keys())
FUTURES_MAIN_MAPPING_COLUMNS = list(TUSHARE_FUTURES_MAPPING_FIELD_MAP.values()) + ["update_time"]

# Stock index futures products and their continuous main-contract series.
FUTURES_EXCHANGE = "CFFEX"
TUSHARE_FUTURES_TYPE_FUTURES = "1"
DEFAULT_INDEX_FUTURES_PRODUCTS = ["IF", "IH", "IC", "IM"]
DEFAULT_CONTINUOUS_CONTRACT_CODES = [f"{product}.CFX" for product in DEFAULT_INDEX_FUTURES_PRODUCTS]
DEFAULT_FUTURES_START_DATE = "20100416"

# Settlement parameters (fut_settle): margin rates and fees per contract per day.
TUSHARE_FUTURES_SETTLE_FIELD_MAP = {
    "ts_code": "contract_code",
    "trade_date": "trade_date",
    "settle": "settle",
    "trading_fee_rate": "trading_fee_rate",
    "trading_fee": "trading_fee",
    "delivery_fee": "delivery_fee",
    "b_hedging_margin_rate": "buy_hedging_margin_rate",
    "s_hedging_margin_rate": "sell_hedging_margin_rate",
    "long_margin_rate": "long_margin_rate",
    "short_margin_rate": "short_margin_rate",
}
FUTURES_SETTLE_COLUMNS = list(TUSHARE_FUTURES_SETTLE_FIELD_MAP.values()) + ["update_time"]

# Member position ranking (fut_holding), keyed by symbol without exchange suffix.
TUSHARE_FUTURES_HOLDING_FIELD_MAP = {
    "trade_date": "trade_date",
    "symbol": "symbol",
    "broker": "broker",
    "vol": "volume",
    "vol_chg": "volume_change",
    "long_hld": "long_holding",
    "long_chg": "long_change",
    "short_hld": "short_holding",
    "short_chg": "short_change",
}
FUTURES_HOLDING_COLUMNS = ["contract_code"] + list(TUSHARE_FUTURES_HOLDING_FIELD_MAP.values()) + ["update_time"]
FUTURES_HOLDING_PAGE_SIZE = 4000
