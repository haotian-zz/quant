"""Constants for daily market event tables (dragon-tiger list, block trades, limit stats)."""

# Dragon-tiger list (top_list): amounts are in 元 unless noted.
TUSHARE_TOP_LIST_FIELD_MAP = {
    "ts_code": "code",
    "name": "name",
    "trade_date": "trade_date",
    "close": "close",
    "pct_change": "pct_chg",
    "turnover_rate": "turnover_rate",
    "amount": "amount",
    "l_sell": "list_sell_amount",
    "l_buy": "list_buy_amount",
    "l_amount": "list_amount",
    "net_amount": "list_net_amount",
    "net_rate": "list_net_ratio",
    "amount_rate": "list_amount_ratio",
    "float_values": "float_market_value",
    "reason": "reason",
}
TUSHARE_TOP_LIST_FIELDS = list(TUSHARE_TOP_LIST_FIELD_MAP.keys())
DRAGON_TIGER_LIST_COLUMNS = list(TUSHARE_TOP_LIST_FIELD_MAP.values()) + ["update_time"]

# Dragon-tiger institution seats (top_inst)
TUSHARE_TOP_INST_FIELD_MAP = {
    "ts_code": "code",
    "trade_date": "trade_date",
    "exalter": "seat_name",
    "side": "side",
    "buy": "buy_amount",
    "buy_rate": "buy_ratio",
    "sell": "sell_amount",
    "sell_rate": "sell_ratio",
    "net_buy": "net_buy_amount",
    "reason": "reason",
}
TUSHARE_TOP_INST_FIELDS = list(TUSHARE_TOP_INST_FIELD_MAP.keys())
DRAGON_TIGER_INST_COLUMNS = list(TUSHARE_TOP_INST_FIELD_MAP.values()) + ["update_time"]

DEFAULT_DRAGON_TIGER_START_DATE = "20100104"

# Block trades (block_trade): vol in 万股, amount in 万元.
TUSHARE_BLOCK_TRADE_FIELD_MAP = {
    "ts_code": "code",
    "trade_date": "trade_date",
    "price": "price",
    "vol": "volume",
    "amount": "amount",
    "buyer": "buyer",
    "seller": "seller",
}
TUSHARE_BLOCK_TRADE_FIELDS = list(TUSHARE_BLOCK_TRADE_FIELD_MAP.keys())
BLOCK_TRADE_COLUMNS = list(TUSHARE_BLOCK_TRADE_FIELD_MAP.values()) + ["update_time"]

TUSHARE_BLOCK_TRADE_VOLUME_TO_LOCAL = 10000
TUSHARE_BLOCK_TRADE_AMOUNT_TO_LOCAL = 10000
DEFAULT_BLOCK_TRADE_START_DATE = "20100104"

# Daily limit-up / limit-down statistics (limit_list_d). Amounts and market values are in 元.
TUSHARE_LIMIT_LIST_FIELD_MAP = {
    "ts_code": "code",
    "name": "name",
    "trade_date": "trade_date",
    "industry": "industry",
    "close": "close",
    "pct_chg": "pct_chg",
    "amount": "amount",
    "limit_amount": "limit_order_amount",
    "float_mv": "float_market_value",
    "total_mv": "total_market_value",
    "turnover_ratio": "turnover_rate",
    "fd_amount": "sealed_amount",
    "first_time": "first_limit_time",
    "last_time": "last_limit_time",
    "open_times": "open_times",
    "up_stat": "limit_streak_stat",
    "limit_times": "consecutive_limit_days",
    "limit": "limit_type",
}
TUSHARE_LIMIT_LIST_FIELDS = list(TUSHARE_LIMIT_LIST_FIELD_MAP.keys())
LIMIT_LIST_COLUMNS = list(TUSHARE_LIMIT_LIST_FIELD_MAP.values()) + ["update_time"]

# Provider limit values: U limit-up, D limit-down, Z touched-but-not-sealed.
TUSHARE_LIMIT_TYPE_MAP = {
    "U": "limit_up",
    "D": "limit_down",
    "Z": "touched",
}
DEFAULT_LIMIT_LIST_START_DATE = "20200103"
