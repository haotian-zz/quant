"""Constants for stock basic metadata tables and provider fields."""

# Tushare fields are copied only into raw files or converted into local fields.
TUSHARE_STOCK_BASIC_FIELDS = [
    "ts_code",
    "symbol",
    "name",
    "area",
    "industry",
    "fullname",
    "enname",
    "cnspell",
    "market",
    "exchange",
    "curr_type",
    "list_status",
    "list_date",
    "delist_date",
    "is_hs",
    "act_name",
    "act_ent_type",
]

# The stock master table avoids provider-specific identifiers.
STOCK_BASIC_COLUMNS = [
    "code",
    "name",
    "full_name",
    "english_name",
    "pinyin",
    "exchange",
    "board",
    "industry",
    "region",
    "currency",
    "list_date",
    "delist_date",
    "status",
    "is_stock_connect",
    "actual_controller",
    "controller_entity_type",
    "update_time",
]

# Keep this mapping near the schema so status values stay consistent.
TUSHARE_LIST_STATUS_MAP = {
    "L": "listed",
    "D": "delisted",
    "P": "suspended",
    "G": "approved",
}

DEFAULT_TUSHARE_LIST_STATUSES = ["L", "D", "P", "G"]
