"""Constants for Shenwan (申万) industry classification and industry indices."""

# Classification tree (index_classify)
TUSHARE_INDEX_CLASSIFY_FIELDS = [
    "index_code",
    "industry_name",
    "level",
    "industry_code",
    "is_pub",
    "parent_code",
    "src",
]

SW_INDUSTRY_COLUMNS = [
    "industry_index_code",
    "industry_name",
    "level",
    "industry_code",
    "is_published",
    "parent_code",
    "source",
    "update_time",
]

# SW2021 is the current Shenwan standard; SW2014 is kept only for backfills.
DEFAULT_SW_SOURCE = "SW2021"
SW_LEVELS = ["L1", "L2", "L3"]

# Membership history (index_member_all)
TUSHARE_INDEX_MEMBER_FIELD_MAP = {
    "ts_code": "code",
    "name": "name",
    "l1_code": "l1_code",
    "l1_name": "l1_name",
    "l2_code": "l2_code",
    "l2_name": "l2_name",
    "l3_code": "l3_code",
    "l3_name": "l3_name",
    "in_date": "in_date",
    "out_date": "out_date",
    "is_new": "is_current",
}
TUSHARE_INDEX_MEMBER_FIELDS = list(TUSHARE_INDEX_MEMBER_FIELD_MAP.keys())
SW_INDUSTRY_MEMBER_COLUMNS = list(TUSHARE_INDEX_MEMBER_FIELD_MAP.values()) + ["update_time"]

SW_INDUSTRY_MEMBER_PAGE_SIZE = 3000

# Industry index daily quotes (sw_daily). vol in 万股, amount and mv in 万元.
TUSHARE_SW_DAILY_FIELDS = [
    "ts_code",
    "trade_date",
    "name",
    "open",
    "high",
    "low",
    "close",
    "change",
    "pct_change",
    "vol",
    "amount",
    "pe",
    "pb",
    "float_mv",
    "total_mv",
]

SW_INDUSTRY_DAILY_COLUMNS = [
    "industry_index_code",
    "trade_date",
    "name",
    "open",
    "high",
    "low",
    "close",
    "change",
    "pct_chg",
    "volume",
    "amount",
    "pe",
    "pb",
    "float_market_value",
    "total_market_value",
    "update_time",
]

TUSHARE_SW_VOLUME_TO_LOCAL = 10000
TUSHARE_SW_AMOUNT_TO_LOCAL = 10000
TUSHARE_SW_MARKET_VALUE_TO_LOCAL = 10000
SW_DAILY_PAGE_SIZE = 4000
DEFAULT_SW_DAILY_START_DATE = "20120801"
