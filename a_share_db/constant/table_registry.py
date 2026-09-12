"""Declarative registry of Tushare tables fetched by the generic table runner.

Each entry describes one formal table: provider API, field mapping, storage
layout and fetch strategy. `a_share_db.utils.table_runner` executes a spec
and `constant/warehouse.py` derives Parquet specs from the same entries, so a
new table is one dictionary here plus its field map in a domain constant.

Layouts:
  single      one CSV, fetched with optional parameter loops and date windows
  per_stock   one CSV per stock from stock_basic (supports --update)
  per_date    one request per trading (or calendar) day, one CSV per year
  per_key     one CSV per key from a key source (contracts, funds, indices)
  per_period  one CSV per quarterly report period
  per_year    one CSV per year, fetched in date windows (announcement tables)
"""

from __future__ import annotations

from a_share_db.constant import paths as P
from a_share_db.constant.auction import AUCTION_COLUMNS, AUCTION_PAGE_SIZE, DEFAULT_AUCTION_START_DATE, TUSHARE_AUCTION_FIELD_MAP
from a_share_db.constant.chips import CHIP_PERF_COLUMNS, CHIP_PERF_PAGE_SIZE, DEFAULT_CHIP_PERF_START_DATE, TUSHARE_CHIP_PERF_FIELD_MAP
from a_share_db.constant.convertible_bond import (
    CB_BASIC_PAGE_SIZE,
    CB_DAILY_SCALES,
    CONVERTIBLE_BOND_BASIC_COLUMNS,
    CONVERTIBLE_BOND_DAILY_COLUMNS,
    DEFAULT_CB_DAILY_START_DATE,
    TUSHARE_CB_BASIC_FIELD_MAP,
    TUSHARE_CB_DAILY_FIELD_MAP,
)
from a_share_db.constant.equity_events import (
    DEFAULT_HOLDER_TRADE_START_DATE,
    DEFAULT_MANAGER_START_DATE,
    DEFAULT_REPURCHASE_START_DATE,
    DEFAULT_SHARE_FLOAT_START_DATE,
    HOLDER_TRADE_COLUMNS,
    MANAGER_COLUMNS,
    MANAGER_REWARD_COLUMNS,
    MANAGER_REWARD_SCALES,
    PLEDGE_COLUMNS,
    PLEDGE_SCALES,
    REPURCHASE_COLUMNS,
    SHARE_FLOAT_COLUMNS,
    TUSHARE_HOLDER_TRADE_FIELD_MAP,
    TUSHARE_HOLDER_TYPE_MAP,
    TUSHARE_MANAGER_FIELD_MAP,
    TUSHARE_MANAGER_REWARD_FIELD_MAP,
    TUSHARE_PLEDGE_FIELD_MAP,
    TUSHARE_REPURCHASE_FIELD_MAP,
    TUSHARE_SHARE_FLOAT_FIELD_MAP,
    TUSHARE_TRADE_DIRECTION_MAP,
)
from a_share_db.constant.financial import (
    AUDIT_COLUMNS,
    DEFAULT_FINANCIAL_START_DATE,
    FINANCIAL_PAGE_SIZE,
    MAIN_BUSINESS_COLUMNS,
    MAIN_BUSINESS_PAGE_SIZE,
    TUSHARE_AUDIT_FIELD_MAP,
    TUSHARE_MAIN_BUSINESS_FIELD_MAP,
    TUSHARE_MAIN_BUSINESS_TYPES,
)
from a_share_db.constant.fund import (
    DEFAULT_FUND_PORTFOLIO_START_DATE,
    FUND_ADJ_COLUMNS,
    FUND_BASIC_COLUMNS,
    FUND_BASIC_PAGE_SIZE,
    FUND_BASIC_SCALES,
    FUND_DAILY_COLUMNS,
    FUND_DAILY_SCALES,
    FUND_DIVIDEND_COLUMNS,
    FUND_MARKETS,
    FUND_NAV_COLUMNS,
    FUND_PORTFOLIO_COLUMNS,
    FUND_PORTFOLIO_PAGE_SIZE,
    FUND_SERIES_PAGE_SIZE,
    FUND_SHARE_COLUMNS,
    FUND_SHARE_SCALES,
    TUSHARE_FUND_ADJ_FIELD_MAP,
    TUSHARE_FUND_BASIC_FIELD_MAP,
    TUSHARE_FUND_DAILY_FIELD_MAP,
    TUSHARE_FUND_DIVIDEND_FIELD_MAP,
    TUSHARE_FUND_NAV_FIELD_MAP,
    TUSHARE_FUND_PORTFOLIO_FIELD_MAP,
    TUSHARE_FUND_SHARE_FIELD_MAP,
)
from a_share_db.constant.futures import (
    FUTURES_HOLDING_COLUMNS,
    FUTURES_HOLDING_PAGE_SIZE,
    FUTURES_SETTLE_COLUMNS,
    TUSHARE_FUTURES_HOLDING_FIELD_MAP,
    TUSHARE_FUTURES_SETTLE_FIELD_MAP,
)
from a_share_db.constant.macro import (
    DEFAULT_ECONOMIC_CALENDAR_START_DATE,
    DEFAULT_LPR_START_DATE,
    DEFAULT_US_TREASURY_START_DATE,
    ECONOMIC_CALENDAR_COLUMNS,
    ECONOMIC_CALENDAR_PAGE_SIZE,
    LPR_COLUMNS,
    PMI_COLUMNS,
    SOCIAL_FINANCING_COLUMNS,
    SOCIAL_FINANCING_SCALES,
    TUSHARE_ECONOMIC_CALENDAR_FIELD_MAP,
    TUSHARE_LPR_FIELD_MAP,
    TUSHARE_PMI_FIELD_MAP,
    TUSHARE_SOCIAL_FINANCING_FIELD_MAP,
    TUSHARE_US_TREASURY_FIELD_MAP,
    US_TREASURY_COLUMNS,
    US_TREASURY_PAGE_SIZE,
)
from a_share_db.constant.market_stats import (
    DEFAULT_MARKET_SUMMARY_START_DATE,
    DEFAULT_STOCK_CONNECT_START_DATE,
    MARKET_SUMMARY_COLUMNS,
    MARKET_SUMMARY_PAGE_SIZE,
    MARKET_SUMMARY_SCALES,
    NORTHBOUND_TOP10_COLUMNS,
    SOUTHBOUND_DAILY_COLUMNS,
    SOUTHBOUND_DAILY_SCALES,
    SOUTHBOUND_TOP10_COLUMNS,
    SZ_MARKET_SUMMARY_COLUMNS,
    SZ_MARKET_SUMMARY_PAGE_SIZE,
    TUSHARE_MARKET_SUMMARY_FIELD_MAP,
    TUSHARE_NORTHBOUND_MARKET_MAP,
    TUSHARE_NORTHBOUND_TOP10_FIELD_MAP,
    TUSHARE_SOUTHBOUND_DAILY_FIELD_MAP,
    TUSHARE_SOUTHBOUND_MARKET_MAP,
    TUSHARE_SOUTHBOUND_TOP10_FIELD_MAP,
    TUSHARE_SZ_MARKET_SUMMARY_FIELD_MAP,
)
from a_share_db.constant.option import (
    DEFAULT_OPTION_START_DATE,
    OPTION_BASIC_COLUMNS,
    OPTION_BASIC_PAGE_SIZE,
    OPTION_DAILY_COLUMNS,
    OPTION_DAILY_SCALES,
    OPTION_EXCHANGES,
    TUSHARE_OPTION_BASIC_FIELD_MAP,
    TUSHARE_OPTION_DAILY_FIELD_MAP,
)
from a_share_db.constant.research import (
    BROKER_RECOMMEND_COLUMNS,
    BROKER_REPORT_COLUMNS,
    BROKER_REPORT_SCALES,
    DEFAULT_BROKER_RECOMMEND_START_MONTH,
    DEFAULT_BROKER_REPORT_START_DATE,
    DEFAULT_INSTITUTION_SURVEY_START_DATE,
    INSTITUTION_SURVEY_COLUMNS,
    INSTITUTION_SURVEY_PAGE_SIZE,
    TUSHARE_BROKER_RECOMMEND_FIELD_MAP,
    TUSHARE_BROKER_REPORT_FIELD_MAP,
    TUSHARE_INSTITUTION_SURVEY_FIELD_MAP,
)
from a_share_db.constant.sector import (
    CI_DAILY_SCALES,
    CITIC_INDUSTRY_DAILY_COLUMNS,
    DC_INDUSTRY_MONEYFLOW_COLUMNS,
    DC_MARKET_MONEYFLOW_COLUMNS,
    DC_SECTOR_DAILY_COLUMNS,
    DC_SECTOR_MEMBER_COLUMNS,
    DEFAULT_CI_DAILY_START_DATE,
    DEFAULT_DC_INDUSTRY_MONEYFLOW_START_DATE,
    DEFAULT_DC_MARKET_MONEYFLOW_START_DATE,
    DEFAULT_DC_SECTOR_START_DATE,
    DEFAULT_THS_DAILY_START_DATE,
    DEFAULT_THS_INDUSTRY_MONEYFLOW_START_DATE,
    GLOBAL_INDEX_DAILY_COLUMNS,
    GLOBAL_INDEX_PAGE_SIZE,
    THS_DAILY_PAGE_SIZE,
    THS_DAILY_SCALES,
    THS_INDEX_COLUMNS,
    THS_INDEX_DAILY_COLUMNS,
    THS_INDEX_MEMBER_COLUMNS,
    THS_INDUSTRY_MONEYFLOW_COLUMNS,
    TUSHARE_CI_DAILY_FIELD_MAP,
    TUSHARE_DC_INDUSTRY_MONEYFLOW_FIELD_MAP,
    TUSHARE_DC_MARKET_MONEYFLOW_FIELD_MAP,
    TUSHARE_DC_SECTOR_FIELD_MAP,
    TUSHARE_DC_SECTOR_MEMBER_FIELD_MAP,
    TUSHARE_INDEX_GLOBAL_FIELD_MAP,
    TUSHARE_THS_DAILY_FIELD_MAP,
    TUSHARE_THS_INDEX_FIELD_MAP,
    TUSHARE_THS_INDEX_TYPE_MAP,
    TUSHARE_THS_INDUSTRY_MONEYFLOW_FIELD_MAP,
    TUSHARE_THS_MEMBER_FIELD_MAP,
)
from a_share_db.constant.sentiment import (
    DC_HOT_COLUMNS,
    DEFAULT_DC_HOT_START_DATE,
    DEFAULT_HOT_MONEY_START_DATE,
    DEFAULT_LIMIT_STREAK_START_DATE,
    DEFAULT_THS_HOT_START_DATE,
    HOT_LIST_PAGE_SIZE,
    HOT_MONEY_DETAIL_COLUMNS,
    HOT_MONEY_LIST_COLUMNS,
    LIMIT_CONCEPT_COLUMNS,
    LIMIT_STREAK_COLUMNS,
    THS_HOT_COLUMNS,
    TUSHARE_DC_HOT_FIELD_MAP,
    TUSHARE_HOT_MONEY_DETAIL_FIELD_MAP,
    TUSHARE_HOT_MONEY_LIST_FIELD_MAP,
    TUSHARE_LIMIT_CONCEPT_FIELD_MAP,
    TUSHARE_LIMIT_STREAK_FIELD_MAP,
    TUSHARE_THS_HOT_FIELD_MAP,
)
from a_share_db.constant.technical import (
    TECHNICAL_FACTOR_COLUMNS,
    TECHNICAL_FACTOR_PAGE_SIZE,
    TECHNICAL_FACTOR_SCALES,
    TUSHARE_TECHNICAL_FACTOR_FIELD_MAP,
)


DEFAULT_TABLE_PAGE_SIZE = 4000
MARKET = P.MARKET_DATA_ROOT
META = P.METADATA_ROOT
FIN = P.FINANCIAL_ROOT
MACRO = P.MACRO_ROOT
RESEARCH = P.DATA_ROOT / "research"
EVENTS = P.DATA_ROOT / "equity_events"
PQ = P.PARQUET_ROOT


def _spec(
    group: str,
    api: str,
    field_map: dict,
    columns: list,
    layout: str,
    csv,
    parquet,
    sort_columns: list,
    text_columns,
    date_columns,
    page_size: int = DEFAULT_TABLE_PAGE_SIZE,
    start: str | None = None,
    scales: dict | None = None,
    value_maps: dict | None = None,
    params: dict | None = None,
    param_loops: list | None = None,
    date_param: str = "trade_date",
    range_params: tuple = ("start_date", "end_date"),
    window_days: int | None = None,
    calendar_days: bool = False,
    keys: str | None = None,
    key_param: str = "ts_code",
    key_constant: str | None = None,
    dedupe_keys: list | None = None,
    end_offset_years: int = 0,
    code_fields: tuple | None = None,
    parquet_key: str | None = None,
    note: str = "",
) -> dict:
    if code_fields is None:
        code_fields = ("ts_code",) if "code" in columns and field_map.get("ts_code") == "code" else ()
    return {
        "group": group,
        "api": api,
        "field_map": field_map,
        "columns": list(columns),
        "layout": layout,
        "csv": csv,
        "parquet": parquet,
        "sort_columns": list(sort_columns),
        "text_columns": set(text_columns) | {"update_time"},
        "date_columns": set(date_columns),
        "page_size": page_size,
        "start": start,
        "scales": scales or {},
        "value_maps": value_maps or {},
        "params": params or {},
        "param_loops": param_loops or [],
        "date_param": date_param,
        "range_params": range_params,
        "window_days": window_days,
        "calendar_days": calendar_days,
        "keys": keys,
        "key_param": key_param,
        "key_constant": key_constant,
        "dedupe_keys": dedupe_keys,
        "end_offset_years": end_offset_years,
        "code_fields": code_fields,
        "code_column": "code" if "code" in columns else None,
        "parquet_key": parquet_key or {"per_stock": "code", "per_date": "year", "per_period": "period", "per_year": "year", "per_key": "index"}.get(layout, "code"),
        "note": note,
    }


TABLE_SPECS: dict[str, dict] = {
    # ------------------------------------------------------------------ research
    "broker_report": _spec(
        "research", "report_rc", TUSHARE_BROKER_REPORT_FIELD_MAP, BROKER_REPORT_COLUMNS, "per_date",
        RESEARCH / "broker_report", PQ / "research" / "broker_report",
        ["report_date", "code", "institution", "author"], {"code", "name", "report_title", "report_type", "classification", "institution", "author", "forecast_period", "rating"}, {"report_date"},
        start=DEFAULT_BROKER_REPORT_START_DATE, date_param="report_date", scales=BROKER_REPORT_SCALES,
        dedupe_keys=["report_date", "code", "institution", "author", "report_title", "forecast_period"],
    ),
    "institution_survey": _spec(
        "research", "stk_surv", TUSHARE_INSTITUTION_SURVEY_FIELD_MAP, INSTITUTION_SURVEY_COLUMNS, "per_year",
        RESEARCH / "institution_survey", PQ / "research" / "institution_survey",
        ["survey_date", "code"], {"code", "name", "visiting_institutions", "reception_place", "reception_mode", "reception_organizer", "institution_type", "company_receivers"}, {"survey_date"},
        page_size=INSTITUTION_SURVEY_PAGE_SIZE, start=DEFAULT_INSTITUTION_SURVEY_START_DATE, window_days=7,
        dedupe_keys=["survey_date", "code", "visiting_institutions", "reception_organizer"],
    ),
    "broker_recommend": _spec(
        "research", "broker_recommend", TUSHARE_BROKER_RECOMMEND_FIELD_MAP, BROKER_RECOMMEND_COLUMNS, "single",
        RESEARCH / "broker_recommend.csv", PQ / "research" / "broker_recommend.parquet",
        ["month", "broker", "code"], {"month", "broker", "code", "name"}, set(),
        keys="months", key_param="month", start=DEFAULT_BROKER_RECOMMEND_START_MONTH, dedupe_keys=["month", "broker", "code"],
    ),
    # ------------------------------------------------------------------ financial supplements
    "audit": _spec(
        "financial", "fina_audit_vip", TUSHARE_AUDIT_FIELD_MAP, AUDIT_COLUMNS, "per_period",
        FIN / "audit", P.PARQUET_FINANCIAL_ROOT / "audit",
        ["code", "report_period", "announce_date"], {"code", "audit_opinion", "audit_firm", "audit_signer"}, {"announce_date", "report_period"},
        page_size=FINANCIAL_PAGE_SIZE, start=DEFAULT_FINANCIAL_START_DATE, key_param="period", dedupe_keys=["code", "report_period", "announce_date"],
    ),
    "main_business": _spec(
        "financial", "fina_mainbz_vip", TUSHARE_MAIN_BUSINESS_FIELD_MAP, MAIN_BUSINESS_COLUMNS, "per_period",
        FIN / "main_business", P.PARQUET_FINANCIAL_ROOT / "main_business",
        ["code", "report_period", "business_type", "business_item"], {"code", "business_item", "business_code", "currency", "business_type"}, {"report_period"},
        page_size=MAIN_BUSINESS_PAGE_SIZE, start=DEFAULT_FINANCIAL_START_DATE, key_param="period",
        param_loops=[{"params": {"type": provider}, "constants": {"business_type": local}} for provider, local in TUSHARE_MAIN_BUSINESS_TYPES.items()],
        dedupe_keys=["code", "report_period", "business_type", "business_item"],
    ),
    # ------------------------------------------------------------------ equity events
    "share_float": _spec(
        "equity_events", "share_float", TUSHARE_SHARE_FLOAT_FIELD_MAP, SHARE_FLOAT_COLUMNS, "per_year",
        EVENTS / "share_float", PQ / "equity_events" / "share_float",
        ["float_date", "code", "holder_name"], {"code", "holder_name", "share_type"}, {"announce_date", "float_date"},
        start=DEFAULT_SHARE_FLOAT_START_DATE, window_days=7, end_offset_years=3,
        dedupe_keys=["float_date", "code", "holder_name", "share_type", "float_shares"],
        note="windows filter float_date; future unlock dates are included",
    ),
    "holder_trade": _spec(
        "equity_events", "stk_holdertrade", TUSHARE_HOLDER_TRADE_FIELD_MAP, HOLDER_TRADE_COLUMNS, "per_year",
        EVENTS / "holder_trade", PQ / "equity_events" / "holder_trade",
        ["announce_date", "code", "holder_name"], {"code", "holder_name", "holder_type", "direction"}, {"announce_date"},
        start=DEFAULT_HOLDER_TRADE_START_DATE, window_days=31,
        value_maps={"holder_type": TUSHARE_HOLDER_TYPE_MAP, "in_de": TUSHARE_TRADE_DIRECTION_MAP},
        dedupe_keys=["announce_date", "code", "holder_name", "direction", "change_shares", "average_price"],
    ),
    "repurchase": _spec(
        "equity_events", "repurchase", TUSHARE_REPURCHASE_FIELD_MAP, REPURCHASE_COLUMNS, "per_year",
        EVENTS / "repurchase", PQ / "equity_events" / "repurchase",
        ["announce_date", "code"], {"code", "process"}, {"announce_date", "report_period", "expiry_date"},
        start=DEFAULT_REPURCHASE_START_DATE, window_days=92, dedupe_keys=["announce_date", "code", "process", "report_period"],
    ),
    "pledge": _spec(
        "equity_events", "pledge_stat", TUSHARE_PLEDGE_FIELD_MAP, PLEDGE_COLUMNS, "per_stock",
        EVENTS / "pledge", PQ / "equity_events" / "pledge",
        ["code", "stat_date"], {"code"}, {"stat_date"}, page_size=1000, scales=PLEDGE_SCALES, dedupe_keys=["code", "stat_date"],
    ),
    "manager": _spec(
        "equity_events", "stk_managers", TUSHARE_MANAGER_FIELD_MAP, MANAGER_COLUMNS, "per_year",
        EVENTS / "manager", PQ / "equity_events" / "manager",
        ["announce_date", "code", "name"], {"code", "name", "gender", "level", "title", "education", "nationality"}, {"announce_date", "birthday", "begin_date", "end_date"},
        start=DEFAULT_MANAGER_START_DATE, window_days=31, dedupe_keys=["announce_date", "code", "name", "title", "begin_date"],
    ),
    "manager_reward": _spec(
        "equity_events", "stk_rewards", TUSHARE_MANAGER_REWARD_FIELD_MAP, MANAGER_REWARD_COLUMNS, "per_stock",
        EVENTS / "manager_reward", PQ / "equity_events" / "manager_reward",
        ["code", "report_period", "name"], {"code", "name", "title"}, {"announce_date", "report_period"},
        page_size=2000, scales=MANAGER_REWARD_SCALES, dedupe_keys=["code", "report_period", "name", "title"],
    ),
    # ------------------------------------------------------------------ funds
    "fund_basic": _spec(
        "fund", "fund_basic", TUSHARE_FUND_BASIC_FIELD_MAP, FUND_BASIC_COLUMNS, "single",
        META / "fund_basic.csv", P.PARQUET_METADATA_ROOT / "fund_basic.parquet",
        ["market", "fund_code"], set(FUND_BASIC_COLUMNS) - {"issue_amount", "management_fee", "custodian_fee", "duration_years", "par_value", "min_subscription_amount", "expected_return", "found_date", "due_date", "list_date", "issue_date", "delist_date", "purchase_start_date", "redemption_start_date"},
        {"found_date", "due_date", "list_date", "issue_date", "delist_date", "purchase_start_date", "redemption_start_date"},
        page_size=FUND_BASIC_PAGE_SIZE, scales=FUND_BASIC_SCALES,
        param_loops=[{"params": {"market": market}} for market in FUND_MARKETS], dedupe_keys=["fund_code"],
    ),
    "fund_portfolio": _spec(
        "fund", "fund_portfolio", TUSHARE_FUND_PORTFOLIO_FIELD_MAP, FUND_PORTFOLIO_COLUMNS, "per_period",
        FIN / "fund_portfolio", P.PARQUET_FINANCIAL_ROOT / "fund_portfolio",
        ["report_period", "fund_code", "code"], {"fund_code", "code"}, {"announce_date", "report_period"},
        page_size=FUND_PORTFOLIO_PAGE_SIZE, start=DEFAULT_FUND_PORTFOLIO_START_DATE, key_param="period",
        code_fields=("symbol",), dedupe_keys=["report_period", "fund_code", "code", "announce_date"],
    ),
    "fund_daily": _spec(
        "fund", "fund_daily", TUSHARE_FUND_DAILY_FIELD_MAP, FUND_DAILY_COLUMNS, "per_key",
        MARKET / "fund_daily", PQ / "fund_daily",
        ["fund_code", "trade_date"], {"fund_code"}, {"trade_date"}, page_size=FUND_SERIES_PAGE_SIZE, scales=FUND_DAILY_SCALES, keys="etf_codes",
    ),
    "fund_nav": _spec(
        "fund", "fund_nav", TUSHARE_FUND_NAV_FIELD_MAP, FUND_NAV_COLUMNS, "per_key",
        MARKET / "fund_nav", PQ / "fund_nav",
        ["fund_code", "nav_date", "announce_date"], {"fund_code", "is_update"}, {"announce_date", "nav_date"}, page_size=FUND_SERIES_PAGE_SIZE, keys="etf_codes",
        dedupe_keys=["fund_code", "nav_date"],
    ),
    "fund_share": _spec(
        "fund", "fund_share", TUSHARE_FUND_SHARE_FIELD_MAP, FUND_SHARE_COLUMNS, "per_key",
        MARKET / "fund_share", PQ / "fund_share",
        ["fund_code", "trade_date"], {"fund_code", "fund_type", "market"}, {"trade_date"}, page_size=FUND_SERIES_PAGE_SIZE, scales=FUND_SHARE_SCALES, keys="etf_codes",
    ),
    "fund_adj": _spec(
        "fund", "fund_adj", TUSHARE_FUND_ADJ_FIELD_MAP, FUND_ADJ_COLUMNS, "per_key",
        MARKET / "fund_adj", PQ / "fund_adj",
        ["fund_code", "trade_date"], {"fund_code"}, {"trade_date"}, page_size=FUND_SERIES_PAGE_SIZE, keys="etf_codes",
    ),
    "fund_dividend": _spec(
        "fund", "fund_div", TUSHARE_FUND_DIVIDEND_FIELD_MAP, FUND_DIVIDEND_COLUMNS, "per_key",
        MARKET / "fund_dividend", PQ / "fund_dividend",
        ["fund_code", "announce_date"], {"fund_code", "process", "base_year"}, {"announce_date", "implementation_announce_date", "base_date", "record_date", "ex_dividend_date", "pay_date", "earnings_pay_date", "net_ex_date", "account_date"},
        page_size=FUND_SERIES_PAGE_SIZE, keys="etf_codes", dedupe_keys=["fund_code", "announce_date", "process", "ex_dividend_date"],
    ),
    # ------------------------------------------------------------------ sectors and themes
    "dc_sector_daily": _spec(
        "sector", "dc_index", TUSHARE_DC_SECTOR_FIELD_MAP, DC_SECTOR_DAILY_COLUMNS, "per_date",
        MARKET / "dc_sector_daily", PQ / "dc_sector_daily",
        ["trade_date", "sector_code"], {"sector_code", "name", "leading_stock_name", "leading_stock_code", "sector_type", "level"}, {"trade_date"},
        start=DEFAULT_DC_SECTOR_START_DATE, code_fields=("leading_code",),
    ),
    "dc_sector_member": _spec(
        "sector", "dc_member", TUSHARE_DC_SECTOR_MEMBER_FIELD_MAP, DC_SECTOR_MEMBER_COLUMNS, "single",
        META / "dc_sector_member.csv", P.PARQUET_METADATA_ROOT / "dc_sector_member.parquet",
        ["sector_code", "code"], {"sector_code", "code", "name"}, {"trade_date"}, page_size=8000,
        params={"trade_date": "$latest_trading_day"}, code_fields=("con_code",), dedupe_keys=["sector_code", "code"],
        note="latest membership snapshot; the provider has no dated history",
    ),
    "ths_index": _spec(
        "sector", "ths_index", TUSHARE_THS_INDEX_FIELD_MAP, THS_INDEX_COLUMNS, "single",
        META / "ths_index.csv", P.PARQUET_METADATA_ROOT / "ths_index.parquet",
        ["index_type", "index_code"], {"index_code", "name", "exchange", "index_type"}, {"list_date"},
        page_size=5000, value_maps={"type": TUSHARE_THS_INDEX_TYPE_MAP}, dedupe_keys=["index_code"],
    ),
    "ths_index_member": _spec(
        "sector", "ths_member", TUSHARE_THS_MEMBER_FIELD_MAP, THS_INDEX_MEMBER_COLUMNS, "single",
        META / "ths_index_member.csv", P.PARQUET_METADATA_ROOT / "ths_index_member.parquet",
        ["index_code", "code"], {"index_code", "code", "name"}, set(), page_size=5000,
        keys="ths_index_codes", code_fields=("con_code",), dedupe_keys=["index_code", "code"],
    ),
    "ths_index_daily": _spec(
        "sector", "ths_daily", TUSHARE_THS_DAILY_FIELD_MAP, THS_INDEX_DAILY_COLUMNS, "per_key",
        MARKET / "ths_index_daily", PQ / "ths_index_daily",
        ["index_code", "trade_date"], {"index_code"}, {"trade_date"}, page_size=THS_DAILY_PAGE_SIZE, start=DEFAULT_THS_DAILY_START_DATE, scales=THS_DAILY_SCALES, keys="ths_index_codes",
    ),
    "citic_industry_daily": _spec(
        "sector", "ci_daily", TUSHARE_CI_DAILY_FIELD_MAP, CITIC_INDUSTRY_DAILY_COLUMNS, "per_date",
        MARKET / "citic_industry_daily", PQ / "citic_industry_daily",
        ["trade_date", "industry_index_code"], {"industry_index_code"}, {"trade_date"}, start=DEFAULT_CI_DAILY_START_DATE, scales=CI_DAILY_SCALES,
    ),
    "global_index_daily": _spec(
        "sector", "index_global", TUSHARE_INDEX_GLOBAL_FIELD_MAP, GLOBAL_INDEX_DAILY_COLUMNS, "per_key",
        MARKET / "global_index_daily", PQ / "global_index_daily",
        ["index_code", "trade_date"], {"index_code"}, {"trade_date"}, page_size=GLOBAL_INDEX_PAGE_SIZE, keys="global_index_codes",
    ),
    "dc_industry_moneyflow": _spec(
        "sector", "moneyflow_ind_dc", TUSHARE_DC_INDUSTRY_MONEYFLOW_FIELD_MAP, DC_INDUSTRY_MONEYFLOW_COLUMNS, "per_date",
        MARKET / "dc_industry_moneyflow", PQ / "dc_industry_moneyflow",
        ["trade_date", "content_type", "sector_code"], {"content_type", "sector_code", "name", "top_small_buy_stock"}, {"trade_date"}, start=DEFAULT_DC_INDUSTRY_MONEYFLOW_START_DATE,
    ),
    "ths_industry_moneyflow": _spec(
        "sector", "moneyflow_ind_ths", TUSHARE_THS_INDUSTRY_MONEYFLOW_FIELD_MAP, THS_INDUSTRY_MONEYFLOW_COLUMNS, "per_date",
        MARKET / "ths_industry_moneyflow", PQ / "ths_industry_moneyflow",
        ["trade_date", "industry_code"], {"industry_code", "industry", "leading_stock"}, {"trade_date"}, start=DEFAULT_THS_INDUSTRY_MONEYFLOW_START_DATE,
    ),
    "dc_market_moneyflow": _spec(
        "sector", "moneyflow_mkt_dc", TUSHARE_DC_MARKET_MONEYFLOW_FIELD_MAP, DC_MARKET_MONEYFLOW_COLUMNS, "single",
        MARKET / "dc_market_moneyflow.csv", PQ / "dc_market_moneyflow.parquet",
        ["trade_date"], set(), {"trade_date"}, start=DEFAULT_DC_MARKET_MONEYFLOW_START_DATE, window_days=366, dedupe_keys=["trade_date"],
    ),
    # ------------------------------------------------------------------ options
    "option_basic": _spec(
        "option", "opt_basic", TUSHARE_OPTION_BASIC_FIELD_MAP, OPTION_BASIC_COLUMNS, "single",
        META / "option_basic.csv", P.PARQUET_METADATA_ROOT / "option_basic.parquet",
        ["exchange", "option_code"], {"option_code", "symbol", "exchange", "name", "product_code", "option_type", "call_put", "exercise_type", "settlement_month", "quote_unit"},
        {"maturity_date", "list_date", "delist_date", "last_exercise_date", "last_delivery_date"},
        page_size=OPTION_BASIC_PAGE_SIZE, param_loops=[{"params": {"exchange": exchange}} for exchange in OPTION_EXCHANGES], dedupe_keys=["option_code"],
    ),
    "option_daily": _spec(
        "option", "opt_daily", TUSHARE_OPTION_DAILY_FIELD_MAP, OPTION_DAILY_COLUMNS, "per_date",
        MARKET / "option_daily", PQ / "option_daily",
        ["trade_date", "exchange", "option_code"], {"option_code", "exchange"}, {"trade_date"},
        start=DEFAULT_OPTION_START_DATE, scales=OPTION_DAILY_SCALES, param_loops=[{"params": {"exchange": exchange}} for exchange in OPTION_EXCHANGES],
    ),
    # ------------------------------------------------------------------ futures supplements
    "futures_settle": _spec(
        "futures", "fut_settle", TUSHARE_FUTURES_SETTLE_FIELD_MAP, FUTURES_SETTLE_COLUMNS, "per_key",
        MARKET / "futures_settle", PQ / "futures_settle",
        ["contract_code", "trade_date"], {"contract_code"}, {"trade_date"}, keys="futures_contracts",
    ),
    "futures_holding": _spec(
        "futures", "fut_holding", TUSHARE_FUTURES_HOLDING_FIELD_MAP, FUTURES_HOLDING_COLUMNS, "per_key",
        MARKET / "futures_holding", PQ / "futures_holding",
        ["trade_date", "broker"], {"contract_code", "symbol", "broker"}, {"trade_date"},
        page_size=FUTURES_HOLDING_PAGE_SIZE, keys="futures_contracts", key_param="symbol", key_constant="contract_code",
        dedupe_keys=["trade_date", "broker"],
    ),
    # ------------------------------------------------------------------ auctions and chips
    "auction_open": _spec(
        "market", "stk_auction_o", TUSHARE_AUCTION_FIELD_MAP, AUCTION_COLUMNS, "per_stock",
        MARKET / "auction_open", PQ / "auction_open",
        ["code", "trade_date"], {"code"}, {"trade_date"}, page_size=AUCTION_PAGE_SIZE, start=DEFAULT_AUCTION_START_DATE,
    ),
    "auction_close": _spec(
        "market", "stk_auction_c", TUSHARE_AUCTION_FIELD_MAP, AUCTION_COLUMNS, "per_stock",
        MARKET / "auction_close", PQ / "auction_close",
        ["code", "trade_date"], {"code"}, {"trade_date"}, page_size=AUCTION_PAGE_SIZE, start=DEFAULT_AUCTION_START_DATE,
    ),
    "chip_distribution": _spec(
        "market", "cyq_perf", TUSHARE_CHIP_PERF_FIELD_MAP, CHIP_PERF_COLUMNS, "per_stock",
        MARKET / "chip_distribution", PQ / "chip_distribution",
        ["code", "trade_date"], {"code"}, {"trade_date"}, page_size=CHIP_PERF_PAGE_SIZE, start=DEFAULT_CHIP_PERF_START_DATE,
    ),
    "technical_factor": _spec(
        "market", "stk_factor_pro", TUSHARE_TECHNICAL_FACTOR_FIELD_MAP, TECHNICAL_FACTOR_COLUMNS, "per_stock",
        MARKET / "technical_factor", PQ / "technical_factor",
        ["code", "trade_date"], {"code"}, {"trade_date"}, page_size=TECHNICAL_FACTOR_PAGE_SIZE, scales=TECHNICAL_FACTOR_SCALES,
    ),
    # ------------------------------------------------------------------ market statistics and stock connect
    "market_summary": _spec(
        "market", "daily_info", TUSHARE_MARKET_SUMMARY_FIELD_MAP, MARKET_SUMMARY_COLUMNS, "single",
        MARKET / "market_summary.csv", PQ / "market_summary.parquet",
        ["trade_date", "market_code"], {"market_code", "market_name", "exchange"}, {"trade_date"},
        page_size=MARKET_SUMMARY_PAGE_SIZE, start=DEFAULT_MARKET_SUMMARY_START_DATE, scales=MARKET_SUMMARY_SCALES, window_days=366, dedupe_keys=["trade_date", "market_code"],
    ),
    "sz_market_summary": _spec(
        "market", "sz_daily_info", TUSHARE_SZ_MARKET_SUMMARY_FIELD_MAP, SZ_MARKET_SUMMARY_COLUMNS, "single",
        MARKET / "sz_market_summary.csv", PQ / "sz_market_summary.parquet",
        ["trade_date", "market_code"], {"market_code"}, {"trade_date"},
        page_size=SZ_MARKET_SUMMARY_PAGE_SIZE, start=DEFAULT_MARKET_SUMMARY_START_DATE, window_days=366, dedupe_keys=["trade_date", "market_code"],
    ),
    "southbound_daily": _spec(
        "market", "ggt_daily", TUSHARE_SOUTHBOUND_DAILY_FIELD_MAP, SOUTHBOUND_DAILY_COLUMNS, "single",
        MARKET / "southbound_daily.csv", PQ / "southbound_daily.parquet",
        ["trade_date"], set(), {"trade_date"}, start=DEFAULT_STOCK_CONNECT_START_DATE, scales=SOUTHBOUND_DAILY_SCALES, window_days=1500, dedupe_keys=["trade_date"],
    ),
    "northbound_top10": _spec(
        "market", "hsgt_top10", TUSHARE_NORTHBOUND_TOP10_FIELD_MAP, NORTHBOUND_TOP10_COLUMNS, "per_date",
        MARKET / "northbound_top10", PQ / "northbound_top10",
        ["trade_date", "connect_market", "rank"], {"code", "name", "connect_market"}, {"trade_date"},
        start=DEFAULT_STOCK_CONNECT_START_DATE, value_maps={"market_type": TUSHARE_NORTHBOUND_MARKET_MAP},
    ),
    "southbound_top10": _spec(
        "market", "ggt_top10", TUSHARE_SOUTHBOUND_TOP10_FIELD_MAP, SOUTHBOUND_TOP10_COLUMNS, "per_date",
        MARKET / "southbound_top10", PQ / "southbound_top10",
        ["trade_date", "connect_market", "rank"], {"hk_code", "name", "connect_market"}, {"trade_date"},
        start=DEFAULT_STOCK_CONNECT_START_DATE, value_maps={"market_type": TUSHARE_SOUTHBOUND_MARKET_MAP},
    ),
    # ------------------------------------------------------------------ sentiment
    "hot_money_list": _spec(
        "sentiment", "hm_list", TUSHARE_HOT_MONEY_LIST_FIELD_MAP, HOT_MONEY_LIST_COLUMNS, "single",
        META / "hot_money_list.csv", P.PARQUET_METADATA_ROOT / "hot_money_list.parquet",
        ["name"], {"name", "description", "organizations"}, set(), dedupe_keys=["name"],
    ),
    "hot_money_detail": _spec(
        "sentiment", "hm_detail", TUSHARE_HOT_MONEY_DETAIL_FIELD_MAP, HOT_MONEY_DETAIL_COLUMNS, "per_date",
        MARKET / "hot_money_detail", PQ / "hot_money_detail",
        ["trade_date", "code", "hot_money_name"], {"code", "name", "hot_money_name", "organizations"}, {"trade_date"}, start=DEFAULT_HOT_MONEY_START_DATE,
    ),
    "ths_hot_list": _spec(
        "sentiment", "ths_hot", TUSHARE_THS_HOT_FIELD_MAP, THS_HOT_COLUMNS, "per_date",
        MARKET / "ths_hot_list", PQ / "ths_hot_list",
        ["trade_date", "list_type", "rank"], {"list_type", "security_code", "name", "concept", "rank_time", "rank_reason"}, {"trade_date"},
        page_size=HOT_LIST_PAGE_SIZE, start=DEFAULT_THS_HOT_START_DATE, code_fields=(),
    ),
    "dc_hot_list": _spec(
        "sentiment", "dc_hot", TUSHARE_DC_HOT_FIELD_MAP, DC_HOT_COLUMNS, "per_date",
        MARKET / "dc_hot_list", PQ / "dc_hot_list",
        ["trade_date", "list_type", "rank"], {"list_type", "security_code", "name", "concept", "rank_time"}, {"trade_date"},
        page_size=HOT_LIST_PAGE_SIZE, start=DEFAULT_DC_HOT_START_DATE, code_fields=(),
    ),
    "limit_streak": _spec(
        "sentiment", "limit_step", TUSHARE_LIMIT_STREAK_FIELD_MAP, LIMIT_STREAK_COLUMNS, "per_date",
        MARKET / "limit_streak", PQ / "limit_streak",
        ["trade_date", "code"], {"code", "name"}, {"trade_date"}, start=DEFAULT_LIMIT_STREAK_START_DATE,
    ),
    "limit_concept": _spec(
        "sentiment", "limit_cpt_list", TUSHARE_LIMIT_CONCEPT_FIELD_MAP, LIMIT_CONCEPT_COLUMNS, "per_date",
        MARKET / "limit_concept", PQ / "limit_concept",
        ["trade_date", "rank"], {"concept_code", "name", "limit_streak_stat"}, {"trade_date"}, start=DEFAULT_LIMIT_STREAK_START_DATE, code_fields=(),
    ),
    # ------------------------------------------------------------------ convertible bonds
    "convertible_bond_basic": _spec(
        "bond", "cb_basic", TUSHARE_CB_BASIC_FIELD_MAP, CONVERTIBLE_BOND_BASIC_COLUMNS, "single",
        META / "convertible_bond_basic.csv", P.PARQUET_METADATA_ROOT / "convertible_bond_basic.parquet",
        ["bond_code"], {"bond_code", "bond_full_name", "bond_short_name", "bond_type", "bond_symbol", "code", "stock_name", "rate_type", "exchange", "rate_clause"},
        {"value_date", "maturity_date", "list_date", "delist_date", "conversion_start_date", "conversion_end_date", "conversion_stop_date"},
        page_size=CB_BASIC_PAGE_SIZE, code_fields=("stk_code",), dedupe_keys=["bond_code"],
    ),
    "convertible_bond_daily": _spec(
        "bond", "cb_daily", TUSHARE_CB_DAILY_FIELD_MAP, CONVERTIBLE_BOND_DAILY_COLUMNS, "per_date",
        MARKET / "convertible_bond_daily", PQ / "convertible_bond_daily",
        ["trade_date", "bond_code"], {"bond_code"}, {"trade_date"}, start=DEFAULT_CB_DAILY_START_DATE, scales=CB_DAILY_SCALES,
    ),
    # ------------------------------------------------------------------ macro supplements
    "lpr": _spec(
        "macro", "shibor_lpr", TUSHARE_LPR_FIELD_MAP, LPR_COLUMNS, "single",
        MACRO / "lpr.csv", P.PARQUET_MACRO_ROOT / "lpr.parquet",
        ["rate_date"], set(), {"rate_date"}, page_size=2000, start=DEFAULT_LPR_START_DATE, window_days=1800, dedupe_keys=["rate_date"],
    ),
    "pmi": _spec(
        "macro", "cn_pmi", TUSHARE_PMI_FIELD_MAP, PMI_COLUMNS, "single",
        MACRO / "pmi.csv", P.PARQUET_MACRO_ROOT / "pmi.parquet",
        ["month"], {"month"}, set(), dedupe_keys=["month"],
    ),
    "social_financing": _spec(
        "macro", "sf_month", TUSHARE_SOCIAL_FINANCING_FIELD_MAP, SOCIAL_FINANCING_COLUMNS, "single",
        MACRO / "social_financing.csv", P.PARQUET_MACRO_ROOT / "social_financing.parquet",
        ["month"], {"month"}, set(), scales=SOCIAL_FINANCING_SCALES, dedupe_keys=["month"],
    ),
    "us_treasury_yield": _spec(
        "macro", "us_tycr", TUSHARE_US_TREASURY_FIELD_MAP, US_TREASURY_COLUMNS, "single",
        MACRO / "us_treasury_yield.csv", P.PARQUET_MACRO_ROOT / "us_treasury_yield.parquet",
        ["rate_date"], set(), {"rate_date"}, page_size=US_TREASURY_PAGE_SIZE, start=DEFAULT_US_TREASURY_START_DATE, window_days=1800, dedupe_keys=["rate_date"],
    ),
    "economic_calendar": _spec(
        "macro", "eco_cal", TUSHARE_ECONOMIC_CALENDAR_FIELD_MAP, ECONOMIC_CALENDAR_COLUMNS, "per_date",
        MACRO / "economic_calendar", P.PARQUET_MACRO_ROOT / "economic_calendar",
        ["event_date", "event_time", "country", "event"], {"event_time", "currency", "country", "event"}, {"event_date"},
        page_size=ECONOMIC_CALENDAR_PAGE_SIZE, start=DEFAULT_ECONOMIC_CALENDAR_START_DATE, date_param="date", calendar_days=True,
        dedupe_keys=["event_date", "event_time", "country", "event"],
    ),
}

TABLE_GROUPS: dict[str, list[str]] = {}
for _name, _spec_dict in TABLE_SPECS.items():
    TABLE_GROUPS.setdefault(_spec_dict["group"], []).append(_name)

# Tier ordering used by the one-command build: research and fundamentals first.
TIER_ONE_TABLES = [
    "broker_report", "audit", "main_business",
    "share_float", "holder_trade", "repurchase", "pledge",
    "fund_basic", "fund_portfolio",
    "dc_sector_daily", "dc_sector_member", "ths_index", "ths_index_member", "ths_index_daily",
    "option_basic", "option_daily",
    "futures_settle", "futures_holding",
    "auction_open", "auction_close",
    "lpr", "pmi", "social_financing", "us_treasury_yield", "economic_calendar",
    "market_summary", "sz_market_summary", "southbound_daily", "northbound_top10", "southbound_top10",
]
TIER_TWO_TABLES = [
    "hot_money_list", "hot_money_detail", "ths_hot_list", "dc_hot_list", "limit_streak", "limit_concept",
    "institution_survey", "broker_recommend", "manager", "manager_reward",
    "chip_distribution",
    "dc_industry_moneyflow", "ths_industry_moneyflow", "dc_market_moneyflow",
    "citic_industry_daily", "global_index_daily",
    "convertible_bond_basic", "convertible_bond_daily",
    "fund_daily", "fund_nav", "fund_share", "fund_adj", "fund_dividend",
    "technical_factor",
]
