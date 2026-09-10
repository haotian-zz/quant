#!/usr/bin/env python3
"""Fetch A-share daily limit-up/limit-down prices from Tushare.

Outputs:
data/market_data/limit_price/{code}.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.limit_price import (
    DEFAULT_LIMIT_PRICE_START_DATE,
    LIMIT_PRICE_COLUMNS,
    LIMIT_PRICE_PAGE_SIZE,
    TUSHARE_LIMIT_PRICE_FIELDS,
)
from a_share_db.constant.paths import LIMIT_PRICE_ROOT, RAW_TUSHARE_ROOT
from a_share_db.utils.cli import (
    add_date_range_arguments,
    add_output_arguments,
    add_run_control_arguments,
    add_stock_selection_arguments,
    add_token_argument,
    require_token,
    run_control_kwargs,
    run_main,
    stock_selection_kwargs,
)
from a_share_db.utils.etl_common import convert_mapped_frame, fetch_paginated
from a_share_db.utils.etl_runners import run_per_stock_etl


DEFAULT_OUTPUT_ROOT = LIMIT_PRICE_ROOT
DEFAULT_RAW_OUTPUT_ROOT = RAW_TUSHARE_ROOT / "limit_price"
FIELD_MAP = dict(zip(TUSHARE_LIMIT_PRICE_FIELDS, LIMIT_PRICE_COLUMNS))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Tushare stk_limit data and build data/market_data/limit_price/{code}.csv."
    )
    add_token_argument(parser)
    add_stock_selection_arguments(parser)
    add_date_range_arguments(parser, default_start=DEFAULT_LIMIT_PRICE_START_DATE, end_defaults_to_today=True)
    add_output_arguments(parser, DEFAULT_OUTPUT_ROOT, DEFAULT_RAW_OUTPUT_ROOT)
    add_run_control_arguments(parser)
    return parser.parse_args()


def fetch_limit_price(pro, ts_code: str, stock: dict, start_date: str | None, end_date: str | None):
    # Pagination keeps full-history requests below the provider row cap.
    return fetch_paginated(
        pro,
        "stk_limit",
        TUSHARE_LIMIT_PRICE_FIELDS,
        page_size=LIMIT_PRICE_PAGE_SIZE,
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
    )


def convert_tushare_limit_price(raw, stock: dict | None = None):
    """Convert raw Tushare stk_limit rows into the local limit_price schema."""
    return convert_mapped_frame(
        raw,
        FIELD_MAP,
        LIMIT_PRICE_COLUMNS,
        sort_columns=["code", "trade_date"],
        date_columns=["trade_date"],
    )


def run_limit_price_etl(token: str, output_root: Path = DEFAULT_OUTPUT_ROOT, raw_output_root: Path = DEFAULT_RAW_OUTPUT_ROOT, **kwargs) -> dict:
    return run_per_stock_etl(
        "fetch_limit_price",
        token,
        fetch_limit_price,
        convert_tushare_limit_price,
        output_root=output_root,
        raw_output_root=raw_output_root,
        **kwargs,
    )


def main() -> int:
    args = parse_args()
    if not require_token(args):
        return 2
    return run_main(
        "fetch_limit_price",
        lambda: run_limit_price_etl(
            token=args.token,
            output_root=args.output_root,
            raw_output_root=args.raw_output_root,
            write_raw=args.with_raw,
            start_date=args.start_date,
            end_date=args.end_date,
            **stock_selection_kwargs(args),
            **run_control_kwargs(args),
        ),
        unit="stocks",
    )


if __name__ == "__main__":
    raise SystemExit(main())
