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

# DuckDB is reserved as a query layer over Parquet, not the current ETL target.
DUCKDB_PATH = WAREHOUSE_ROOT / "a_share.duckdb"

# ETL logs record command status without becoming part of the data schema.
ETL_LOG_PATH = LOG_ROOT / "etl_log.csv"
