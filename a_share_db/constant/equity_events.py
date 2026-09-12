"""Constants for shareholder and corporate-action event tables."""

# Lock-up releases (share_float). float_share is in 股, float_ratio in %.
TUSHARE_SHARE_FLOAT_FIELD_MAP = {
    "ts_code": "code",
    "ann_date": "announce_date",
    "float_date": "float_date",
    "float_share": "float_shares",
    "float_ratio": "float_ratio",
    "holder_name": "holder_name",
    "share_type": "share_type",
}
SHARE_FLOAT_COLUMNS = list(TUSHARE_SHARE_FLOAT_FIELD_MAP.values()) + ["update_time"]
DEFAULT_SHARE_FLOAT_START_DATE = "20070101"

# Insider / major holder trades (stk_holdertrade).
TUSHARE_HOLDER_TRADE_FIELD_MAP = {
    "ts_code": "code",
    "ann_date": "announce_date",
    "holder_name": "holder_name",
    "holder_type": "holder_type",
    "in_de": "direction",
    "change_vol": "change_shares",
    "change_ratio": "change_ratio",
    "after_share": "shares_after",
    "after_ratio": "ratio_after",
    "avg_price": "average_price",
    "total_share": "total_shares",
}
HOLDER_TRADE_COLUMNS = list(TUSHARE_HOLDER_TRADE_FIELD_MAP.values()) + ["update_time"]
TUSHARE_HOLDER_TYPE_MAP = {"G": "executive", "P": "individual", "C": "company"}
TUSHARE_TRADE_DIRECTION_MAP = {"IN": "increase", "DE": "decrease"}
DEFAULT_HOLDER_TRADE_START_DATE = "20070101"

# Share repurchases (repurchase). vol in 股, amount in 元.
TUSHARE_REPURCHASE_FIELD_MAP = {
    "ts_code": "code",
    "ann_date": "announce_date",
    "end_date": "report_period",
    "proc": "process",
    "exp_date": "expiry_date",
    "vol": "volume",
    "amount": "amount",
    "high_limit": "price_high_limit",
    "low_limit": "price_low_limit",
}
REPURCHASE_COLUMNS = list(TUSHARE_REPURCHASE_FIELD_MAP.values()) + ["update_time"]
DEFAULT_REPURCHASE_START_DATE = "20050101"

# Pledge statistics (pledge_stat). Share counts are provider 万股 -> 股.
TUSHARE_PLEDGE_FIELD_MAP = {
    "ts_code": "code",
    "end_date": "stat_date",
    "pledge_count": "pledge_count",
    "unrest_pledge": "unrestricted_pledged_shares",
    "rest_pledge": "restricted_pledged_shares",
    "total_share": "total_shares",
    "pledge_ratio": "pledge_ratio",
}
PLEDGE_COLUMNS = list(TUSHARE_PLEDGE_FIELD_MAP.values()) + ["update_time"]
PLEDGE_SCALES = {"unrest_pledge": 10000, "rest_pledge": 10000, "total_share": 10000}

# Managers (stk_managers) and manager compensation (stk_rewards, reward 万元 -> 元).
TUSHARE_MANAGER_FIELD_MAP = {
    "ts_code": "code",
    "ann_date": "announce_date",
    "name": "name",
    "gender": "gender",
    "lev": "level",
    "title": "title",
    "edu": "education",
    "national": "nationality",
    "birthday": "birthday",
    "begin_date": "begin_date",
    "end_date": "end_date",
}
MANAGER_COLUMNS = list(TUSHARE_MANAGER_FIELD_MAP.values()) + ["update_time"]
DEFAULT_MANAGER_START_DATE = "19900101"

TUSHARE_MANAGER_REWARD_FIELD_MAP = {
    "ts_code": "code",
    "ann_date": "announce_date",
    "end_date": "report_period",
    "name": "name",
    "title": "title",
    "reward": "reward",
    "hold_vol": "holding_shares",
}
MANAGER_REWARD_COLUMNS = list(TUSHARE_MANAGER_REWARD_FIELD_MAP.values()) + ["update_time"]
MANAGER_REWARD_SCALES = {"reward": 10000}
