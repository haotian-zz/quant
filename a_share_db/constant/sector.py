"""Constants for theme/sector classifications and their indices (东财, 同花顺, 中信, global)."""

# Eastmoney sectors (dc_index / dc_member), covered from 2024-12-20.
TUSHARE_DC_SECTOR_FIELD_MAP = {
    "ts_code": "sector_code",
    "trade_date": "trade_date",
    "name": "name",
    "leading": "leading_stock_name",
    "leading_code": "leading_stock_code",
    "pct_change": "pct_chg",
    "leading_pct": "leading_stock_pct_chg",
    "total_mv": "total_market_value",
    "turnover_rate": "turnover_rate",
    "up_num": "up_count",
    "down_num": "down_count",
    "idx_type": "sector_type",
    "level": "level",
}
DC_SECTOR_DAILY_COLUMNS = list(TUSHARE_DC_SECTOR_FIELD_MAP.values()) + ["update_time"]
DEFAULT_DC_SECTOR_START_DATE = "20241220"

TUSHARE_DC_SECTOR_MEMBER_FIELD_MAP = {
    "trade_date": "trade_date",
    "ts_code": "sector_code",
    "con_code": "code",
    "name": "name",
}
DC_SECTOR_MEMBER_COLUMNS = list(TUSHARE_DC_SECTOR_MEMBER_FIELD_MAP.values()) + ["update_time"]

# Tonghuashun indices (ths_index / ths_member / ths_daily).
TUSHARE_THS_INDEX_FIELD_MAP = {
    "ts_code": "index_code",
    "name": "name",
    "count": "member_count",
    "exchange": "exchange",
    "list_date": "list_date",
    "type": "index_type",
}
THS_INDEX_COLUMNS = list(TUSHARE_THS_INDEX_FIELD_MAP.values()) + ["update_time"]
TUSHARE_THS_INDEX_TYPE_MAP = {"N": "concept", "I": "industry", "R": "region", "S": "special", "ST": "style", "TH": "theme", "BB": "broad"}

TUSHARE_THS_MEMBER_FIELD_MAP = {
    "ts_code": "index_code",
    "con_code": "code",
    "con_name": "name",
}
THS_INDEX_MEMBER_COLUMNS = list(TUSHARE_THS_MEMBER_FIELD_MAP.values()) + ["update_time"]

# ths_daily vol is provider 万股 -> 股.
TUSHARE_THS_DAILY_FIELD_MAP = {
    "ts_code": "index_code",
    "trade_date": "trade_date",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "pre_close": "pre_close",
    "avg_price": "average_price",
    "change": "change",
    "pct_change": "pct_chg",
    "vol": "volume",
    "turnover_rate": "turnover_rate",
}
THS_INDEX_DAILY_COLUMNS = list(TUSHARE_THS_DAILY_FIELD_MAP.values()) + ["update_time"]
THS_DAILY_SCALES = {"vol": 10000}
THS_DAILY_PAGE_SIZE = 3000
DEFAULT_THS_DAILY_START_DATE = "20140101"

# CITIC industry indices (ci_daily): vol 万股 -> 股, amount 万元 -> 元.
TUSHARE_CI_DAILY_FIELD_MAP = {
    "ts_code": "industry_index_code",
    "trade_date": "trade_date",
    "open": "open",
    "low": "low",
    "high": "high",
    "close": "close",
    "pre_close": "pre_close",
    "change": "change",
    "pct_change": "pct_chg",
    "vol": "volume",
    "amount": "amount",
}
CITIC_INDUSTRY_DAILY_COLUMNS = list(TUSHARE_CI_DAILY_FIELD_MAP.values()) + ["update_time"]
CI_DAILY_SCALES = {"vol": 10000, "amount": 10000}
DEFAULT_CI_DAILY_START_DATE = "20100104"

# Global indices (index_global): provider codes such as XIN9, HSI, DJI, SPX, IXIC.
TUSHARE_INDEX_GLOBAL_FIELD_MAP = {
    "ts_code": "index_code",
    "trade_date": "trade_date",
    "open": "open",
    "close": "close",
    "high": "high",
    "low": "low",
    "pre_close": "pre_close",
    "change": "change",
    "pct_chg": "pct_chg",
    "swing": "swing",
    "vol": "volume",
}
GLOBAL_INDEX_DAILY_COLUMNS = list(TUSHARE_INDEX_GLOBAL_FIELD_MAP.values()) + ["update_time"]
GLOBAL_INDEX_PAGE_SIZE = 4000

# Sector/market money flow (Eastmoney and Tonghuashun aggregates), amounts in 元.
TUSHARE_DC_INDUSTRY_MONEYFLOW_FIELD_MAP = {
    "trade_date": "trade_date",
    "content_type": "content_type",
    "ts_code": "sector_code",
    "name": "name",
    "pct_change": "pct_chg",
    "close": "close",
    "net_amount": "net_amount",
    "net_amount_rate": "net_amount_ratio",
    "buy_elg_amount": "buy_extra_large_amount",
    "buy_elg_amount_rate": "buy_extra_large_ratio",
    "buy_lg_amount": "buy_large_amount",
    "buy_lg_amount_rate": "buy_large_ratio",
    "buy_md_amount": "buy_medium_amount",
    "buy_md_amount_rate": "buy_medium_ratio",
    "buy_sm_amount": "buy_small_amount",
    "buy_sm_amount_rate": "buy_small_ratio",
    "buy_sm_amount_stock": "top_small_buy_stock",
    "rank": "rank",
}
DC_INDUSTRY_MONEYFLOW_COLUMNS = list(TUSHARE_DC_INDUSTRY_MONEYFLOW_FIELD_MAP.values()) + ["update_time"]
DEFAULT_DC_INDUSTRY_MONEYFLOW_START_DATE = "20240102"

TUSHARE_THS_INDUSTRY_MONEYFLOW_FIELD_MAP = {
    "trade_date": "trade_date",
    "ts_code": "industry_code",
    "industry": "industry",
    "lead_stock": "leading_stock",
    "close": "close",
    "pct_change": "pct_chg",
    "company_num": "company_count",
    "pct_change_stock": "leading_stock_pct_chg",
    "close_price": "leading_stock_close",
    "net_buy_amount": "net_buy_amount",
    "net_sell_amount": "net_sell_amount",
    "net_amount": "net_amount",
}
THS_INDUSTRY_MONEYFLOW_COLUMNS = list(TUSHARE_THS_INDUSTRY_MONEYFLOW_FIELD_MAP.values()) + ["update_time"]
DEFAULT_THS_INDUSTRY_MONEYFLOW_START_DATE = "20250102"

TUSHARE_DC_MARKET_MONEYFLOW_FIELD_MAP = {
    "trade_date": "trade_date",
    "close_sh": "sh_close",
    "pct_change_sh": "sh_pct_chg",
    "close_sz": "sz_close",
    "pct_change_sz": "sz_pct_chg",
    "net_amount": "net_amount",
    "net_amount_rate": "net_amount_ratio",
    "buy_elg_amount": "buy_extra_large_amount",
    "buy_elg_amount_rate": "buy_extra_large_ratio",
    "buy_lg_amount": "buy_large_amount",
    "buy_lg_amount_rate": "buy_large_ratio",
    "buy_md_amount": "buy_medium_amount",
    "buy_md_amount_rate": "buy_medium_ratio",
    "buy_sm_amount": "buy_small_amount",
    "buy_sm_amount_rate": "buy_small_ratio",
}
DC_MARKET_MONEYFLOW_COLUMNS = list(TUSHARE_DC_MARKET_MONEYFLOW_FIELD_MAP.values()) + ["update_time"]
DEFAULT_DC_MARKET_MONEYFLOW_START_DATE = "20240102"
