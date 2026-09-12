"""Constants for short-term sentiment tables (hot money, hot lists, limit streaks)."""

TUSHARE_HOT_MONEY_LIST_FIELD_MAP = {
    "name": "name",
    "desc": "description",
    "orgs": "organizations",
}
HOT_MONEY_LIST_COLUMNS = list(TUSHARE_HOT_MONEY_LIST_FIELD_MAP.values()) + ["update_time"]

# hm_detail amounts are in 元.
TUSHARE_HOT_MONEY_DETAIL_FIELD_MAP = {
    "trade_date": "trade_date",
    "ts_code": "code",
    "ts_name": "name",
    "buy_amount": "buy_amount",
    "sell_amount": "sell_amount",
    "net_amount": "net_amount",
    "hm_name": "hot_money_name",
    "hm_orgs": "organizations",
}
HOT_MONEY_DETAIL_COLUMNS = list(TUSHARE_HOT_MONEY_DETAIL_FIELD_MAP.values()) + ["update_time"]
DEFAULT_HOT_MONEY_START_DATE = "20230101"

# Hot lists (ths_hot / dc_hot). Ranked securities may be stocks, ETFs or concepts,
# so the provider code is kept as text instead of being reduced to six digits.
TUSHARE_THS_HOT_FIELD_MAP = {
    "trade_date": "trade_date",
    "data_type": "list_type",
    "ts_code": "security_code",
    "ts_name": "name",
    "rank": "rank",
    "pct_change": "pct_chg",
    "current_price": "price",
    "hot": "heat",
    "concept": "concept",
    "rank_time": "rank_time",
    "rank_reason": "rank_reason",
}
THS_HOT_COLUMNS = list(TUSHARE_THS_HOT_FIELD_MAP.values()) + ["update_time"]
DEFAULT_THS_HOT_START_DATE = "20240101"

TUSHARE_DC_HOT_FIELD_MAP = {key: value for key, value in TUSHARE_THS_HOT_FIELD_MAP.items() if key != "rank_reason"}
DC_HOT_COLUMNS = list(TUSHARE_DC_HOT_FIELD_MAP.values()) + ["update_time"]
DEFAULT_DC_HOT_START_DATE = "20250101"
HOT_LIST_PAGE_SIZE = 2000

# Consecutive limit-up streaks (limit_step) and limit-up concepts (limit_cpt_list).
TUSHARE_LIMIT_STREAK_FIELD_MAP = {
    "ts_code": "code",
    "name": "name",
    "trade_date": "trade_date",
    "nums": "consecutive_limit_days",
}
LIMIT_STREAK_COLUMNS = list(TUSHARE_LIMIT_STREAK_FIELD_MAP.values()) + ["update_time"]

TUSHARE_LIMIT_CONCEPT_FIELD_MAP = {
    "ts_code": "concept_code",
    "name": "name",
    "trade_date": "trade_date",
    "days": "days",
    "up_stat": "limit_streak_stat",
    "cons_nums": "consecutive_limit_count",
    "up_nums": "limit_up_count",
    "pct_chg": "pct_chg",
    "rank": "rank",
}
LIMIT_CONCEPT_COLUMNS = list(TUSHARE_LIMIT_CONCEPT_FIELD_MAP.values()) + ["update_time"]
DEFAULT_LIMIT_STREAK_START_DATE = "20240101"
