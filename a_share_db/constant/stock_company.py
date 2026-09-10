"""Constants for listed company profile metadata."""

# Ordered provider field -> local column. Lists below are derived from it.
TUSHARE_STOCK_COMPANY_FIELD_MAP = {
    "ts_code": "code",
    "exchange": "exchange",
    "com_name": "company_name",
    "com_id": "company_id",
    "chairman": "chairman",
    "manager": "general_manager",
    "secretary": "board_secretary",
    "reg_capital": "registered_capital",
    "setup_date": "setup_date",
    "province": "province",
    "city": "city",
    "introduction": "introduction",
    "website": "website",
    "email": "email",
    "office": "office_address",
    "employees": "employees",
    "main_business": "main_business",
    "business_scope": "business_scope",
}
TUSHARE_STOCK_COMPANY_FIELDS = list(TUSHARE_STOCK_COMPANY_FIELD_MAP.keys())
STOCK_COMPANY_COLUMNS = list(TUSHARE_STOCK_COMPANY_FIELD_MAP.values()) + ["update_time"]

# Tushare reg_capital is in 万元; local registered_capital is in 元.
TUSHARE_REGISTERED_CAPITAL_TO_LOCAL = 10000

# stock_company is queried per exchange; BSE is included for completeness.
STOCK_COMPANY_EXCHANGES = ["SSE", "SZSE", "BSE"]
