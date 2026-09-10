"""Constants for Parquet and warehouse build scripts."""

PARQUET_TABLES = ["metadata", "daily", "adj_factor", "daily_basic", "minute"]
PARQUET_ALL_TABLES = ["all"]

# First Parquet version mirrors the current per-stock CSV layout.
PARQUET_METADATA_FILES = ["stock_basic", "trade_calendar"]


# ---------------------------------------------------------------------------
# Second-generation tables. Each spec drives Parquet discovery and typing:
#   layout        "dir" (one CSV per key under csv_root) or "file" (single CSV)
#   text_columns  columns kept as strings; every other non-date column is numeric
#   date_columns  ISO date columns stored as Parquet dates
# ---------------------------------------------------------------------------
from a_share_db.constant import paths as _paths
from a_share_db.constant.events import BLOCK_TRADE_COLUMNS, DRAGON_TIGER_INST_COLUMNS, DRAGON_TIGER_LIST_COLUMNS, LIMIT_LIST_COLUMNS
from a_share_db.constant.financial import (
    BALANCE_SHEET_COLUMNS,
    CASH_FLOW_COLUMNS,
    DISCLOSURE_DATE_COLUMNS,
    DIVIDEND_COLUMNS,
    EXPRESS_COLUMNS,
    FINANCIAL_INDICATOR_COLUMNS,
    FORECAST_COLUMNS,
    INCOME_COLUMNS,
)
from a_share_db.constant.holders import HOLDER_NUMBER_COLUMNS, TOP10_HOLDER_COLUMNS
from a_share_db.constant.index import INDEX_BASIC_COLUMNS, INDEX_DAILY_BASIC_COLUMNS, INDEX_DAILY_COLUMNS, INDEX_WEIGHT_COLUMNS
from a_share_db.constant.industry import SW_INDUSTRY_COLUMNS, SW_INDUSTRY_DAILY_COLUMNS, SW_INDUSTRY_MEMBER_COLUMNS
from a_share_db.constant.ipo import IPO_COLUMNS
from a_share_db.constant.limit_price import LIMIT_PRICE_COLUMNS
from a_share_db.constant.macro import CPI_COLUMNS, GDP_COLUMNS, MONEY_SUPPLY_COLUMNS, PPI_COLUMNS, SHIBOR_COLUMNS
from a_share_db.constant.margin import MARGIN_COLUMNS, MARGIN_SUMMARY_COLUMNS
from a_share_db.constant.moneyflow import MONEYFLOW_COLUMNS
from a_share_db.constant.name_change import STOCK_NAME_HISTORY_COLUMNS
from a_share_db.constant.st_stock import ST_STOCK_COLUMNS
from a_share_db.constant.stock_company import STOCK_COMPANY_COLUMNS
from a_share_db.constant.stock_connect import STOCK_CONNECT_CONSTITUENT_COLUMNS, STOCK_CONNECT_FLOW_COLUMNS, STOCK_CONNECT_HOLD_COLUMNS
from a_share_db.constant.suspend import SUSPEND_COLUMNS

_STATEMENT_TEXT = {"code", "statement_type", "company_type", "period_type", "is_update", "update_time"}
_STATEMENT_DATES = {"announce_date", "actual_announce_date", "report_period"}


def _spec(layout, columns, text_columns, date_columns, csv=None, parquet=None, key="code"):
    return {
        "layout": layout,
        # key names what a directory layout's file stems are: code, period, year or index.
        "key": key,
        "columns": list(columns),
        "text_columns": set(text_columns) | {"update_time"},
        "date_columns": set(date_columns),
        "csv": csv,
        "parquet": parquet,
    }


EXTENDED_PARQUET_TABLES = {
    # market_data, per key
    "limit_price": _spec("dir", LIMIT_PRICE_COLUMNS, {"code"}, {"trade_date"}, _paths.LIMIT_PRICE_ROOT, _paths.PARQUET_ROOT / "limit_price"),
    "suspend": _spec("dir", SUSPEND_COLUMNS, {"code", "suspend_timing", "suspend_type"}, {"trade_date"}, _paths.SUSPEND_ROOT, _paths.PARQUET_ROOT / "suspend", key="year"),
    "st_stock": _spec("dir", ST_STOCK_COLUMNS, {"code", "name", "st_type", "st_type_name"}, {"trade_date"}, _paths.ST_STOCK_ROOT, _paths.PARQUET_ROOT / "st_stock", key="year"),
    "moneyflow": _spec("dir", MONEYFLOW_COLUMNS, {"code"}, {"trade_date"}, _paths.MONEYFLOW_ROOT, _paths.PARQUET_ROOT / "moneyflow"),
    "margin": _spec("dir", MARGIN_COLUMNS, {"code"}, {"trade_date"}, _paths.MARGIN_ROOT, _paths.PARQUET_ROOT / "margin"),
    "stock_connect_hold": _spec("dir", STOCK_CONNECT_HOLD_COLUMNS, {"code", "connect_market"}, {"trade_date"}, _paths.STOCK_CONNECT_HOLD_ROOT, _paths.PARQUET_ROOT / "stock_connect_hold"),
    "index_daily": _spec("dir", INDEX_DAILY_COLUMNS, {"index_code"}, {"trade_date"}, _paths.INDEX_DAILY_ROOT, _paths.PARQUET_ROOT / "index_daily", key="index"),
    "index_daily_basic": _spec("dir", INDEX_DAILY_BASIC_COLUMNS, {"index_code"}, {"trade_date"}, _paths.INDEX_DAILY_BASIC_ROOT, _paths.PARQUET_ROOT / "index_daily_basic", key="index"),
    "index_weight": _spec("dir", INDEX_WEIGHT_COLUMNS, {"index_code", "code"}, {"trade_date"}, _paths.INDEX_WEIGHT_ROOT, _paths.PARQUET_ROOT / "index_weight", key="index"),
    "sw_industry_daily": _spec("dir", SW_INDUSTRY_DAILY_COLUMNS, {"industry_index_code", "name"}, {"trade_date"}, _paths.SW_INDUSTRY_DAILY_ROOT, _paths.PARQUET_ROOT / "sw_industry_daily", key="index"),
    "dragon_tiger_list": _spec("dir", DRAGON_TIGER_LIST_COLUMNS, {"code", "name", "reason"}, {"trade_date"}, _paths.DRAGON_TIGER_LIST_ROOT, _paths.PARQUET_ROOT / "dragon_tiger_list", key="year"),
    "dragon_tiger_inst": _spec("dir", DRAGON_TIGER_INST_COLUMNS, {"code", "seat_name", "side", "reason"}, {"trade_date"}, _paths.DRAGON_TIGER_INST_ROOT, _paths.PARQUET_ROOT / "dragon_tiger_inst", key="year"),
    "block_trade": _spec("dir", BLOCK_TRADE_COLUMNS, {"code", "buyer", "seller"}, {"trade_date"}, _paths.BLOCK_TRADE_ROOT, _paths.PARQUET_ROOT / "block_trade", key="year"),
    "limit_list": _spec("dir", LIMIT_LIST_COLUMNS, {"code", "name", "industry", "first_limit_time", "last_limit_time", "limit_streak_stat", "limit_type"}, {"trade_date"}, _paths.LIMIT_LIST_ROOT, _paths.PARQUET_ROOT / "limit_list", key="year"),
    # market_data, single files
    "margin_summary": _spec("file", MARGIN_SUMMARY_COLUMNS, {"exchange"}, {"trade_date"}, _paths.MARGIN_SUMMARY_PATH, _paths.PARQUET_ROOT / "margin_summary.parquet"),
    "stock_connect_flow": _spec("file", STOCK_CONNECT_FLOW_COLUMNS, set(), {"trade_date"}, _paths.STOCK_CONNECT_FLOW_PATH, _paths.PARQUET_ROOT / "stock_connect_flow.parquet"),
    # metadata
    "stock_name_history": _spec("file", STOCK_NAME_HISTORY_COLUMNS, {"code", "name", "change_reason"}, {"start_date", "end_date", "announce_date"}, _paths.STOCK_NAME_HISTORY_PATH, _paths.PARQUET_METADATA_ROOT / "stock_name_history.parquet"),
    "stock_company": _spec("file", STOCK_COMPANY_COLUMNS, set(STOCK_COMPANY_COLUMNS) - {"registered_capital", "employees", "setup_date"}, {"setup_date"}, _paths.STOCK_COMPANY_PATH, _paths.PARQUET_METADATA_ROOT / "stock_company.parquet"),
    "ipo": _spec("file", IPO_COLUMNS, {"code", "subscription_code", "name"}, {"ipo_date", "list_date"}, _paths.IPO_PATH, _paths.PARQUET_METADATA_ROOT / "ipo.parquet"),
    "stock_connect_constituent": _spec("file", STOCK_CONNECT_CONSTITUENT_COLUMNS, {"code", "connect_market", "is_current"}, {"in_date", "out_date"}, _paths.STOCK_CONNECT_CONSTITUENT_PATH, _paths.PARQUET_METADATA_ROOT / "stock_connect_constituent.parquet"),
    "index_basic": _spec("file", INDEX_BASIC_COLUMNS, set(INDEX_BASIC_COLUMNS) - {"base_point", "base_date", "list_date", "expire_date"}, {"base_date", "list_date", "expire_date"}, _paths.INDEX_BASIC_PATH, _paths.PARQUET_METADATA_ROOT / "index_basic.parquet"),
    "sw_industry": _spec("file", SW_INDUSTRY_COLUMNS, set(SW_INDUSTRY_COLUMNS), set(), _paths.SW_INDUSTRY_PATH, _paths.PARQUET_METADATA_ROOT / "sw_industry.parquet"),
    "sw_industry_member": _spec("file", SW_INDUSTRY_MEMBER_COLUMNS, set(SW_INDUSTRY_MEMBER_COLUMNS) - {"in_date", "out_date"}, {"in_date", "out_date"}, _paths.SW_INDUSTRY_MEMBER_PATH, _paths.PARQUET_METADATA_ROOT / "sw_industry_member.parquet"),
    # financial, per report period or per stock
    "income": _spec("dir", INCOME_COLUMNS, _STATEMENT_TEXT, _STATEMENT_DATES, _paths.INCOME_ROOT, _paths.PARQUET_FINANCIAL_ROOT / "income", key="period"),
    "balance_sheet": _spec("dir", BALANCE_SHEET_COLUMNS, _STATEMENT_TEXT, _STATEMENT_DATES, _paths.BALANCE_SHEET_ROOT, _paths.PARQUET_FINANCIAL_ROOT / "balance_sheet", key="period"),
    "cash_flow": _spec("dir", CASH_FLOW_COLUMNS, _STATEMENT_TEXT, _STATEMENT_DATES, _paths.CASH_FLOW_ROOT, _paths.PARQUET_FINANCIAL_ROOT / "cash_flow", key="period"),
    "indicator": _spec("dir", FINANCIAL_INDICATOR_COLUMNS, {"code", "is_update"}, {"announce_date", "report_period"}, _paths.FINANCIAL_INDICATOR_ROOT, _paths.PARQUET_FINANCIAL_ROOT / "indicator", key="period"),
    "forecast": _spec("dir", FORECAST_COLUMNS, {"code", "forecast_type", "summary", "change_reason"}, {"announce_date", "report_period", "first_announce_date"}, _paths.FORECAST_ROOT, _paths.PARQUET_FINANCIAL_ROOT / "forecast", key="period"),
    "express": _spec("dir", EXPRESS_COLUMNS, {"code", "performance_summary", "is_audited", "remark"}, {"announce_date", "report_period"}, _paths.EXPRESS_ROOT, _paths.PARQUET_FINANCIAL_ROOT / "express", key="period"),
    "disclosure_date": _spec("dir", DISCLOSURE_DATE_COLUMNS, {"code", "modified_dates"}, {"announce_date", "report_period", "planned_date", "actual_date"}, _paths.DISCLOSURE_DATE_ROOT, _paths.PARQUET_FINANCIAL_ROOT / "disclosure_date", key="period"),
    "dividend": _spec("dir", DIVIDEND_COLUMNS, {"code", "process"}, {"report_period", "announce_date", "record_date", "ex_dividend_date", "pay_date", "share_listing_date", "implementation_announce_date", "base_date"}, _paths.DIVIDEND_ROOT, _paths.PARQUET_FINANCIAL_ROOT / "dividend"),
    "holder_number": _spec("dir", HOLDER_NUMBER_COLUMNS, {"code"}, {"announce_date", "report_period"}, _paths.HOLDER_NUMBER_ROOT, _paths.PARQUET_FINANCIAL_ROOT / "holder_number"),
    "top10_holders": _spec("dir", TOP10_HOLDER_COLUMNS, {"code", "holder_name", "holder_type"}, {"announce_date", "report_period"}, _paths.TOP10_HOLDERS_ROOT, _paths.PARQUET_FINANCIAL_ROOT / "top10_holders", key="period"),
    "top10_float_holders": _spec("dir", TOP10_HOLDER_COLUMNS, {"code", "holder_name", "holder_type"}, {"announce_date", "report_period"}, _paths.TOP10_FLOAT_HOLDERS_ROOT, _paths.PARQUET_FINANCIAL_ROOT / "top10_float_holders", key="period"),
    # macro
    "shibor": _spec("file", SHIBOR_COLUMNS, set(), {"rate_date"}, _paths.SHIBOR_PATH, _paths.PARQUET_MACRO_ROOT / "shibor.parquet"),
    "gdp": _spec("file", GDP_COLUMNS, {"quarter"}, set(), _paths.GDP_PATH, _paths.PARQUET_MACRO_ROOT / "gdp.parquet"),
    "cpi": _spec("file", CPI_COLUMNS, {"month"}, set(), _paths.CPI_PATH, _paths.PARQUET_MACRO_ROOT / "cpi.parquet"),
    "ppi": _spec("file", PPI_COLUMNS, {"month"}, set(), _paths.PPI_PATH, _paths.PARQUET_MACRO_ROOT / "ppi.parquet"),
    "money_supply": _spec("file", MONEY_SUPPLY_COLUMNS, {"month"}, set(), _paths.MONEY_SUPPLY_PATH, _paths.PARQUET_MACRO_ROOT / "money_supply.parquet"),
}

# Group shortcuts accepted by build_parquet --tables.
PARQUET_TABLE_GROUPS = {
    "extended": list(EXTENDED_PARQUET_TABLES),
    "financial": ["income", "balance_sheet", "cash_flow", "indicator", "forecast", "express", "disclosure_date", "dividend", "holder_number", "top10_holders", "top10_float_holders"],
    "macro": ["shibor", "gdp", "cpi", "ppi", "money_supply"],
}
