"""Project filesystem paths."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

# All generated CSV data lives under data/, which is ignored by git.
DATA_ROOT = PROJECT_ROOT / "data"

# Directory groups make scripts share the same storage layout.
METADATA_ROOT = DATA_ROOT / "metadata"
MARKET_DATA_ROOT = DATA_ROOT / "market_data"
RAW_ROOT = DATA_ROOT / "raw"
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

# Raw provider files are optional and kept away from curated local tables.
RAW_DAILY_ROOT = RAW_ROOT / "daily"
RAW_TUSHARE_DAILY_NONE_ROOT = RAW_DAILY_ROOT / "tushare" / "none"
RAW_ADJ_FACTOR_ROOT = RAW_ROOT / "adj_factor"
RAW_TUSHARE_ADJ_FACTOR_ROOT = RAW_ADJ_FACTOR_ROOT / "tushare"

# ETL logs record command status without becoming part of the data schema.
ETL_LOG_PATH = LOG_ROOT / "etl_log.csv"
