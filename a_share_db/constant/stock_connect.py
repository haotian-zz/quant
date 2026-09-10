"""Constants for Shanghai/Shenzhen-Hong Kong Stock Connect tables."""

# Constituent history (hs_const)
TUSHARE_STOCK_CONNECT_CONST_FIELDS = [
    "ts_code",
    "hs_type",
    "in_date",
    "out_date",
    "is_new",
]

STOCK_CONNECT_CONSTITUENT_COLUMNS = [
    "code",
    "connect_market",
    "in_date",
    "out_date",
    "is_current",
    "update_time",
]

# Provider hs_type values map to the local exchange the northbound channel trades on.
TUSHARE_HS_TYPE_MAP = {
    "SH": "SSE",
    "SZ": "SZSE",
}
STOCK_CONNECT_QUERY_TYPES = ["SH", "SZ"]
STOCK_CONNECT_QUERY_IS_NEW = ["1", "0"]

# Northbound holdings per stock (hk_hold)
TUSHARE_STOCK_CONNECT_HOLD_FIELDS = [
    "ts_code",
    "trade_date",
    "vol",
    "ratio",
    "exchange",
]

STOCK_CONNECT_HOLD_COLUMNS = [
    "code",
    "trade_date",
    "hold_shares",
    "hold_ratio",
    "connect_market",
    "update_time",
]

DEFAULT_STOCK_CONNECT_HOLD_START_DATE = "20160101"
STOCK_CONNECT_HOLD_PAGE_SIZE = 3000

# Aggregate northbound/southbound flow (moneyflow_hsgt)
TUSHARE_STOCK_CONNECT_FLOW_FIELDS = [
    "trade_date",
    "ggt_ss",
    "ggt_sz",
    "hgt",
    "sgt",
    "north_money",
    "south_money",
]

STOCK_CONNECT_FLOW_COLUMNS = [
    "trade_date",
    "southbound_sh_amount",
    "southbound_sz_amount",
    "northbound_sh_amount",
    "northbound_sz_amount",
    "northbound_amount",
    "southbound_amount",
    "update_time",
]

# Tushare moneyflow_hsgt values are in 百万元; local amounts are in 元.
TUSHARE_STOCK_CONNECT_FLOW_TO_LOCAL = 1_000_000
DEFAULT_STOCK_CONNECT_FLOW_START_DATE = "20141117"
STOCK_CONNECT_FLOW_PAGE_SIZE = 300
