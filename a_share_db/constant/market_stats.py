"""Constants for market-wide statistics and Stock Connect leaderboards."""

# SSE market overview (daily_info): shares/volume 亿股 -> 股, money 亿元 -> 元, trades 万笔 -> 笔.
TUSHARE_MARKET_SUMMARY_FIELD_MAP = {
    "trade_date": "trade_date",
    "ts_code": "market_code",
    "ts_name": "market_name",
    "exchange": "exchange",
    "com_count": "company_count",
    "total_share": "total_shares",
    "float_share": "float_shares",
    "total_mv": "total_market_value",
    "float_mv": "float_market_value",
    "amount": "amount",
    "vol": "volume",
    "trans_count": "trade_count",
    "pe": "pe",
    "tr": "turnover_rate",
}
MARKET_SUMMARY_COLUMNS = list(TUSHARE_MARKET_SUMMARY_FIELD_MAP.values()) + ["update_time"]
MARKET_SUMMARY_SCALES = {"total_share": 1e8, "float_share": 1e8, "total_mv": 1e8, "float_mv": 1e8, "amount": 1e8, "vol": 1e8, "trans_count": 1e4}
DEFAULT_MARKET_SUMMARY_START_DATE = "20100101"
MARKET_SUMMARY_PAGE_SIZE = 4000

# SZSE market overview (sz_daily_info): provider units are already 元 and 股.
TUSHARE_SZ_MARKET_SUMMARY_FIELD_MAP = {
    "trade_date": "trade_date",
    "ts_code": "market_code",
    "count": "company_count",
    "amount": "amount",
    "vol": "volume",
    "total_share": "total_shares",
    "total_mv": "total_market_value",
    "float_share": "float_shares",
    "float_mv": "float_market_value",
}
SZ_MARKET_SUMMARY_COLUMNS = list(TUSHARE_SZ_MARKET_SUMMARY_FIELD_MAP.values()) + ["update_time"]
SZ_MARKET_SUMMARY_PAGE_SIZE = 2000

# Southbound aggregate turnover (ggt_daily): 亿元 / 亿股 -> 元 / 股.
TUSHARE_SOUTHBOUND_DAILY_FIELD_MAP = {
    "trade_date": "trade_date",
    "buy_amount": "buy_amount",
    "buy_volume": "buy_volume",
    "sell_amount": "sell_amount",
    "sell_volume": "sell_volume",
}
SOUTHBOUND_DAILY_COLUMNS = list(TUSHARE_SOUTHBOUND_DAILY_FIELD_MAP.values()) + ["update_time"]
SOUTHBOUND_DAILY_SCALES = {"buy_amount": 1e8, "buy_volume": 1e8, "sell_amount": 1e8, "sell_volume": 1e8}
DEFAULT_STOCK_CONNECT_START_DATE = "20141117"

# Northbound top-10 (hsgt_top10): amounts in 元; market_type 1 沪股通 3 深股通.
TUSHARE_NORTHBOUND_TOP10_FIELD_MAP = {
    "trade_date": "trade_date",
    "ts_code": "code",
    "name": "name",
    "close": "close",
    "change": "pct_chg",
    "rank": "rank",
    "market_type": "connect_market",
    "amount": "amount",
    "net_amount": "net_amount",
    "buy": "buy_amount",
    "sell": "sell_amount",
}
NORTHBOUND_TOP10_COLUMNS = list(TUSHARE_NORTHBOUND_TOP10_FIELD_MAP.values()) + ["update_time"]
TUSHARE_NORTHBOUND_MARKET_MAP = {"1": "SSE", "3": "SZSE"}

# Southbound top-10 (ggt_top10): Hong Kong codes stay as provider text (00700.HK).
TUSHARE_SOUTHBOUND_TOP10_FIELD_MAP = {
    "trade_date": "trade_date",
    "ts_code": "hk_code",
    "name": "name",
    "close": "close",
    "p_change": "pct_chg",
    "rank": "rank",
    "market_type": "connect_market",
    "amount": "amount",
    "net_amount": "net_amount",
    "sh_amount": "sh_amount",
    "sh_net_amount": "sh_net_amount",
    "sh_buy": "sh_buy_amount",
    "sh_sell": "sh_sell_amount",
    "sz_amount": "sz_amount",
    "sz_net_amount": "sz_net_amount",
    "sz_buy": "sz_buy_amount",
    "sz_sell": "sz_sell_amount",
}
SOUTHBOUND_TOP10_COLUMNS = list(TUSHARE_SOUTHBOUND_TOP10_FIELD_MAP.values()) + ["update_time"]
TUSHARE_SOUTHBOUND_MARKET_MAP = {"2": "SSE", "4": "SZSE"}
