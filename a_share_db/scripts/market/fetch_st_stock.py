#!/usr/bin/env python3
"""Fetch the daily ST / risk-warning stock list from Tushare by trade date.

Outputs:
data/market_data/st_stock/{year}.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.paths import RAW_TUSHARE_ROOT, ST_STOCK_ROOT
from a_share_db.constant.st_stock import (
    DEFAULT_ST_STOCK_START_DATE,
    ST_STOCK_COLUMNS,
    TUSHARE_ST_STOCK_FIELDS,
)
from a_share_db.utils.cli import (
    add_calendar_arguments,
    add_date_range_arguments,
    add_output_arguments,
    add_run_control_arguments,
    add_token_argument,
    require_token,
    run_control_kwargs,
    run_main,
)
from a_share_db.utils.etl_common import convert_mapped_frame, fetch_paginated
from a_share_db.utils.etl_runners import run_per_date_etl


DEFAULT_OUTPUT_ROOT = ST_STOCK_ROOT
DEFAULT_RAW_OUTPUT_ROOT = RAW_TUSHARE_ROOT / "st_stock"
FIELD_MAP = dict(zip(TUSHARE_ST_STOCK_FIELDS, ST_STOCK_COLUMNS))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Tushare stock_st data by trade date and build data/market_data/st_stock/{year}.csv."
    )
    add_token_argument(parser)
    add_date_range_arguments(parser, default_start=DEFAULT_ST_STOCK_START_DATE, end_defaults_to_today=True)
    add_calendar_arguments(parser)
    add_output_arguments(parser, DEFAULT_OUTPUT_ROOT, DEFAULT_RAW_OUTPUT_ROOT)
    add_run_control_arguments(parser)
    return parser.parse_args()


def fetch_st_stock(pro, trade_date: str):
    return fetch_paginated(pro, "stock_st", TUSHARE_ST_STOCK_FIELDS, trade_date=trade_date)


def convert_tushare_st_stock(raw):
    """Convert raw Tushare stock_st rows into the local st_stock schema."""
    return convert_mapped_frame(
        raw,
        FIELD_MAP,
        ST_STOCK_COLUMNS,
        sort_columns=["trade_date", "code"],
        date_columns=["trade_date"],
    )


def run_st_stock_etl(token: str, output_root: Path = DEFAULT_OUTPUT_ROOT, raw_output_root: Path = DEFAULT_RAW_OUTPUT_ROOT, **kwargs) -> dict:
    return run_per_date_etl(
        "fetch_st_stock",
        token,
        fetch_st_stock,
        convert_tushare_st_stock,
        output_root=output_root,
        raw_output_root=raw_output_root,
        **kwargs,
    )


def main() -> int:
    args = parse_args()
    if not require_token(args):
        return 2
    return run_main(
        "fetch_st_stock",
        lambda: run_st_stock_etl(
            token=args.token,
            output_root=args.output_root,
            raw_output_root=args.raw_output_root,
            write_raw=args.with_raw,
            start_date=args.start_date,
            end_date=args.end_date,
            trade_calendar_path=args.trade_calendar,
            limit_days=args.limit_days,
            **run_control_kwargs(args),
        ),
        unit="trading days",
    )


if __name__ == "__main__":
    raise SystemExit(main())
