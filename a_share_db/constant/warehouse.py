"""Constants for Parquet and warehouse build scripts."""

PARQUET_TABLES = ["metadata", "daily", "adj_factor", "daily_basic", "minute"]
PARQUET_ALL_TABLES = ["all"]

# First Parquet version mirrors the current per-stock CSV layout.
PARQUET_METADATA_FILES = ["stock_basic", "trade_calendar"]
