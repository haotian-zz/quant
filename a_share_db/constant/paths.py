"""Project filesystem paths."""

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

# QuantDB is the canonical local data volume. Keeping this explicit prevents
# future ETL runs from silently recreating a large project-local data directory.
QUANTDB_VOLUME_ROOT = Path(os.getenv("A_SHARE_DB_QUANTDB_VOLUME", "/Volumes/QuantDB")).expanduser()
DEFAULT_DATA_ROOT = QUANTDB_VOLUME_ROOT / "a_share_db" / "data"
DATA_ROOT = Path(os.getenv("A_SHARE_DB_DATA_ROOT", str(DEFAULT_DATA_ROOT))).expanduser()
PROJECT_DATA_ROOT = PROJECT_ROOT / "data"


def ensure_data_root_available() -> Path:
    """Return the configured data root, failing before writes if QuantDB is absent."""
    if DATA_ROOT == DEFAULT_DATA_ROOT and not QUANTDB_VOLUME_ROOT.is_mount():
        raise RuntimeError(
            f"QuantDB volume is not mounted at {QUANTDB_VOLUME_ROOT}. "
            "Mount the disk before running ETL jobs, or set A_SHARE_DB_DATA_ROOT explicitly."
        )
    return DATA_ROOT


def data_relative_path(path: Path) -> Path | None:
    """Return path relative to the configured data root when possible."""
    path = Path(path)
    roots = [DATA_ROOT, PROJECT_DATA_ROOT]
    for root in roots:
        try:
            return path.resolve(strict=False).relative_to(root.resolve(strict=False))
        except ValueError:
            pass
        try:
            return path.relative_to(root)
        except ValueError:
            pass
    return None


def build_data_backup_path(path: Path, backup_root: Path, backup_timestamp: str) -> Path:
    """Build a backup path preserving data-root-relative layout."""
    relative_path = data_relative_path(path)
    if relative_path is None:
        path = Path(path)
        if path.is_absolute():
            relative_path = Path("external").joinpath(*path.parts[1:])
        else:
            relative_path = path
    return Path(backup_root) / backup_timestamp / relative_path


ensure_data_root_available()

# Directory groups make scripts share the same storage layout.
METADATA_ROOT = DATA_ROOT / "metadata"
MARKET_DATA_ROOT = DATA_ROOT / "market_data"
RAW_ROOT = DATA_ROOT / "raw"
PARQUET_ROOT = DATA_ROOT / "parquet"
WAREHOUSE_ROOT = DATA_ROOT / "warehouse"
LOG_ROOT = DATA_ROOT / "logs"
BACKUP_ROOT = DATA_ROOT / "backups"

# Metadata tables are small project-level CSV files.
STOCK_BASIC_PATH = METADATA_ROOT / "stock_basic.csv"
RAW_TUSHARE_STOCK_BASIC_PATH = METADATA_ROOT / "raw_tushare_stock_basic.csv"
TRADE_CALENDAR_PATH = METADATA_ROOT / "trade_calendar.csv"
RAW_TUSHARE_TRADE_CALENDAR_PATH = METADATA_ROOT / "raw_tushare_trade_calendar.csv"

# Market data is split by table and adjustment type.
DAILY_ROOT = MARKET_DATA_ROOT / "daily"
DAILY_NONE_ROOT = DAILY_ROOT / "none"
DAILY_QFQ_ROOT = DAILY_ROOT / "qfq"
DAILY_HFQ_ROOT = DAILY_ROOT / "hfq"
ADJ_FACTOR_ROOT = MARKET_DATA_ROOT / "adj_factor"
DAILY_BASIC_ROOT = MARKET_DATA_ROOT / "daily_basic"
MINUTE_ROOT = MARKET_DATA_ROOT / "minute"

# Raw provider files are optional and kept away from curated local tables.
RAW_DAILY_ROOT = RAW_ROOT / "daily"
RAW_TUSHARE_DAILY_NONE_ROOT = RAW_DAILY_ROOT / "tushare" / "none"
RAW_ADJ_FACTOR_ROOT = RAW_ROOT / "adj_factor"
RAW_TUSHARE_ADJ_FACTOR_ROOT = RAW_ADJ_FACTOR_ROOT / "tushare"
RAW_DAILY_BASIC_ROOT = RAW_ROOT / "daily_basic"
RAW_TUSHARE_DAILY_BASIC_ROOT = RAW_DAILY_BASIC_ROOT / "tushare"
RAW_MINUTE_ROOT = RAW_ROOT / "minute"
RAW_TUSHARE_MINUTE_ROOT = RAW_MINUTE_ROOT / "tushare"

# Parquet is the planned formal analysis layer built from local CSV outputs.
PARQUET_METADATA_ROOT = PARQUET_ROOT / "metadata"
PARQUET_DAILY_ROOT = PARQUET_ROOT / "daily"
PARQUET_MINUTE_ROOT = PARQUET_ROOT / "minute"
PARQUET_ADJ_FACTOR_ROOT = PARQUET_ROOT / "adj_factor"
PARQUET_DAILY_BASIC_ROOT = PARQUET_ROOT / "daily_basic"

# Second-generation tables keep the same split: curated CSV under market_data,
# metadata, financial or macro roots; raw provider rows only under raw/.
LIMIT_PRICE_ROOT = MARKET_DATA_ROOT / "limit_price"
SUSPEND_ROOT = MARKET_DATA_ROOT / "suspend"
ST_STOCK_ROOT = MARKET_DATA_ROOT / "st_stock"
MONEYFLOW_ROOT = MARKET_DATA_ROOT / "moneyflow"
MARGIN_ROOT = MARKET_DATA_ROOT / "margin"
MARGIN_SUMMARY_PATH = MARKET_DATA_ROOT / "margin_summary.csv"
STOCK_CONNECT_HOLD_ROOT = MARKET_DATA_ROOT / "stock_connect_hold"
STOCK_CONNECT_FLOW_PATH = MARKET_DATA_ROOT / "stock_connect_flow.csv"
INDEX_DAILY_ROOT = MARKET_DATA_ROOT / "index_daily"
INDEX_DAILY_BASIC_ROOT = MARKET_DATA_ROOT / "index_daily_basic"
INDEX_WEIGHT_ROOT = MARKET_DATA_ROOT / "index_weight"
SW_INDUSTRY_DAILY_ROOT = MARKET_DATA_ROOT / "sw_industry_daily"
DRAGON_TIGER_LIST_ROOT = MARKET_DATA_ROOT / "dragon_tiger_list"
DRAGON_TIGER_INST_ROOT = MARKET_DATA_ROOT / "dragon_tiger_inst"
BLOCK_TRADE_ROOT = MARKET_DATA_ROOT / "block_trade"
LIMIT_LIST_ROOT = MARKET_DATA_ROOT / "limit_list"

STOCK_NAME_HISTORY_PATH = METADATA_ROOT / "stock_name_history.csv"
STOCK_COMPANY_PATH = METADATA_ROOT / "stock_company.csv"
IPO_PATH = METADATA_ROOT / "ipo.csv"
STOCK_CONNECT_CONSTITUENT_PATH = METADATA_ROOT / "stock_connect_constituent.csv"
INDEX_BASIC_PATH = METADATA_ROOT / "index_basic.csv"
SW_INDUSTRY_PATH = METADATA_ROOT / "sw_industry.csv"
SW_INDUSTRY_MEMBER_PATH = METADATA_ROOT / "sw_industry_member.csv"

# Financial statements are partitioned by report period because the provider
# bulk interfaces return one period for the whole market per request.
FINANCIAL_ROOT = DATA_ROOT / "financial"
INCOME_ROOT = FINANCIAL_ROOT / "income"
BALANCE_SHEET_ROOT = FINANCIAL_ROOT / "balance_sheet"
CASH_FLOW_ROOT = FINANCIAL_ROOT / "cash_flow"
FINANCIAL_INDICATOR_ROOT = FINANCIAL_ROOT / "indicator"
FORECAST_ROOT = FINANCIAL_ROOT / "forecast"
EXPRESS_ROOT = FINANCIAL_ROOT / "express"
DISCLOSURE_DATE_ROOT = FINANCIAL_ROOT / "disclosure_date"
DIVIDEND_ROOT = FINANCIAL_ROOT / "dividend"
HOLDER_NUMBER_ROOT = FINANCIAL_ROOT / "holder_number"
TOP10_HOLDERS_ROOT = FINANCIAL_ROOT / "top10_holders"
TOP10_FLOAT_HOLDERS_ROOT = FINANCIAL_ROOT / "top10_float_holders"

MACRO_ROOT = DATA_ROOT / "macro"
SHIBOR_PATH = MACRO_ROOT / "shibor.csv"
GDP_PATH = MACRO_ROOT / "gdp.csv"
CPI_PATH = MACRO_ROOT / "cpi.csv"
PPI_PATH = MACRO_ROOT / "ppi.csv"
MONEY_SUPPLY_PATH = MACRO_ROOT / "money_supply.csv"

RAW_TUSHARE_ROOT = RAW_ROOT / "tushare"
PARQUET_FINANCIAL_ROOT = PARQUET_ROOT / "financial"
PARQUET_MACRO_ROOT = PARQUET_ROOT / "macro"

# DuckDB is reserved as a query layer over Parquet, not the current ETL target.
DUCKDB_PATH = WAREHOUSE_ROOT / "a_share.duckdb"

# ETL logs record command status without becoming part of the data schema.
ETL_LOG_PATH = LOG_ROOT / "etl_log.csv"
