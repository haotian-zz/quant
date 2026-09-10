#!/usr/bin/env python3
"""Fetch index daily quotes and index valuation from Tushare.

Outputs:
data/market_data/index_daily/{index_code}.csv         (--tables daily)
data/market_data/index_daily_basic/{index_code}.csv   (--tables daily_basic)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.index import (
    DEFAULT_INDEX_DAILY_BASIC_START_DATE,
    DEFAULT_INDEX_DAILY_CODES,
    DEFAULT_INDEX_START_DATE,
    INDEX_DAILY_BASIC_COLUMNS,
    INDEX_DAILY_BASIC_PAGE_SIZE,
    INDEX_DAILY_COLUMNS,
    INDEX_DAILY_PAGE_SIZE,
    TUSHARE_INDEX_AMOUNT_TO_LOCAL,
    TUSHARE_INDEX_DAILY_BASIC_FIELDS,
    TUSHARE_INDEX_DAILY_FIELDS,
    TUSHARE_INDEX_MARKET_VALUE_TO_LOCAL,
    TUSHARE_INDEX_SHARE_TO_LOCAL,
    TUSHARE_INDEX_VOLUME_TO_LOCAL,
)
from a_share_db.constant.paths import INDEX_DAILY_BASIC_ROOT, INDEX_DAILY_ROOT, RAW_TUSHARE_ROOT
from a_share_db.utils.cli import (
    add_date_range_arguments,
    add_run_control_arguments,
    add_token_argument,
    report_result,
    require_token,
    run_control_kwargs,
)
from a_share_db.utils.etl_common import convert_mapped_frame, fetch_paginated
from a_share_db.utils.etl_runners import run_per_key_etl


INDEX_TABLES = ["daily", "daily_basic"]
DAILY_FIELD_MAP = dict(zip(TUSHARE_INDEX_DAILY_FIELDS, INDEX_DAILY_COLUMNS))
DAILY_BASIC_FIELD_MAP = dict(zip(TUSHARE_INDEX_DAILY_BASIC_FIELDS, INDEX_DAILY_BASIC_COLUMNS))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Tushare index_daily / index_dailybasic and build per-index CSV files."
    )
    add_token_argument(parser)
    parser.add_argument("--tables", nargs="+", choices=INDEX_TABLES, default=INDEX_TABLES, help="Tables to fetch. Default: daily daily_basic.")
    parser.add_argument("--index-codes", nargs="+", default=DEFAULT_INDEX_DAILY_CODES, help="Index codes such as 000300.SH. Default: project benchmark list.")
    add_date_range_arguments(parser, default_start=None, end_defaults_to_today=True)
    parser.add_argument("--with-raw", action="store_true", help="Also write raw provider CSV files under data/raw/tushare/.")
    add_run_control_arguments(parser)
    return parser.parse_args()


def convert_tushare_index_daily(raw, index_code: str | None = None):
    """Convert raw Tushare index_daily rows into the local index_daily schema."""
    return convert_mapped_frame(
        raw,
        DAILY_FIELD_MAP,
        INDEX_DAILY_COLUMNS,
        sort_columns=["index_code", "trade_date"],
        date_columns=["trade_date"],
        scales={"vol": TUSHARE_INDEX_VOLUME_TO_LOCAL, "amount": TUSHARE_INDEX_AMOUNT_TO_LOCAL},
        code_fields=(),
        code_column=None,
    )


def convert_tushare_index_daily_basic(raw, index_code: str | None = None):
    """Convert raw Tushare index_dailybasic rows into the local index_daily_basic schema."""
    return convert_mapped_frame(
        raw,
        DAILY_BASIC_FIELD_MAP,
        INDEX_DAILY_BASIC_COLUMNS,
        sort_columns=["index_code", "trade_date"],
        date_columns=["trade_date"],
        scales={
            "total_mv": TUSHARE_INDEX_MARKET_VALUE_TO_LOCAL,
            "float_mv": TUSHARE_INDEX_MARKET_VALUE_TO_LOCAL,
            "total_share": TUSHARE_INDEX_SHARE_TO_LOCAL,
            "float_share": TUSHARE_INDEX_SHARE_TO_LOCAL,
            "free_share": TUSHARE_INDEX_SHARE_TO_LOCAL,
        },
        code_fields=(),
        code_column=None,
    )


# table -> (api, fields, page size, converter, output root, default start)
TABLE_SPECS = {
    "daily": ("index_daily", TUSHARE_INDEX_DAILY_FIELDS, INDEX_DAILY_PAGE_SIZE, convert_tushare_index_daily, INDEX_DAILY_ROOT, DEFAULT_INDEX_START_DATE),
    "daily_basic": ("index_dailybasic", TUSHARE_INDEX_DAILY_BASIC_FIELDS, INDEX_DAILY_BASIC_PAGE_SIZE, convert_tushare_index_daily_basic, INDEX_DAILY_BASIC_ROOT, DEFAULT_INDEX_DAILY_BASIC_START_DATE),
}


def run_index_table_etl(table: str, token: str, index_codes=DEFAULT_INDEX_DAILY_CODES, start_date: str | None = None, end_date: str | None = None, **kwargs) -> dict:
    api_name, fields, page_size, convert_fn, output_root, default_start = TABLE_SPECS[table]
    start_date = start_date or default_start

    def fetch_fn(pro, index_code: str):
        return fetch_paginated(pro, api_name, fields, page_size=page_size, ts_code=index_code, start_date=start_date, end_date=end_date)

    return run_per_key_etl(
        f"fetch_index_{table}",
        token,
        keys=list(index_codes),
        fetch_fn=fetch_fn,
        convert_fn=convert_fn,
        output_path_fn=lambda index_code: Path(output_root) / f"{index_code}.csv",
        raw_output_path_fn=lambda index_code: RAW_TUSHARE_ROOT / f"index_{table}" / f"{index_code}.csv",
        **kwargs,
    )


def main() -> int:
    args = parse_args()
    if not require_token(args):
        return 2
    exit_code = 0
    for table in args.tables:
        try:
            result = run_index_table_etl(
                table,
                token=args.token,
                index_codes=args.index_codes,
                start_date=args.start_date,
                end_date=args.end_date,
                write_raw=args.with_raw,
                **run_control_kwargs(args),
            )
        except Exception as exc:
            print(f"fetch_index_{table} failed: {exc}", file=sys.stderr)
            exit_code = 1
            continue
        exit_code = max(exit_code, report_result(result, f"fetch_index_{table}", unit="indices"))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
