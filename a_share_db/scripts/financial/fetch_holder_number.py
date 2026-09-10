#!/usr/bin/env python3
"""Fetch shareholder counts per stock from Tushare.

Outputs:
data/financial/holder_number/{code}.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.holders import (
    HOLDER_NUMBER_COLUMNS,
    HOLDER_NUMBER_PAGE_SIZE,
    TUSHARE_HOLDER_NUMBER_FIELDS,
)
from a_share_db.constant.paths import HOLDER_NUMBER_ROOT, RAW_TUSHARE_ROOT
from a_share_db.utils.cli import (
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


DEFAULT_OUTPUT_ROOT = HOLDER_NUMBER_ROOT
DEFAULT_RAW_OUTPUT_ROOT = RAW_TUSHARE_ROOT / "holder_number"
FIELD_MAP = dict(zip(TUSHARE_HOLDER_NUMBER_FIELDS, HOLDER_NUMBER_COLUMNS))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Tushare stk_holdernumber data and build data/financial/holder_number/{code}.csv."
    )
    add_token_argument(parser)
    add_stock_selection_arguments(parser)
    add_output_arguments(parser, DEFAULT_OUTPUT_ROOT, DEFAULT_RAW_OUTPUT_ROOT)
    add_run_control_arguments(parser)
    return parser.parse_args()


def fetch_holder_number(pro, ts_code: str, stock: dict, start_date: str | None, end_date: str | None):
    # The provider pages this interface at 100 rows; pagination collects all of them.
    return fetch_paginated(pro, "stk_holdernumber", TUSHARE_HOLDER_NUMBER_FIELDS, page_size=HOLDER_NUMBER_PAGE_SIZE, ts_code=ts_code)


def convert_tushare_holder_number(raw, stock: dict | None = None):
    """Convert raw Tushare stk_holdernumber rows into the local holder_number schema."""
    frame = convert_mapped_frame(
        raw,
        FIELD_MAP,
        HOLDER_NUMBER_COLUMNS,
        sort_columns=["code", "report_period", "announce_date"],
        date_columns=["announce_date", "report_period"],
    )
    return frame.drop_duplicates(subset=["code", "report_period", "announce_date"], keep="last").reset_index(drop=True)


def run_holder_number_etl(token: str, output_root: Path = DEFAULT_OUTPUT_ROOT, raw_output_root: Path = DEFAULT_RAW_OUTPUT_ROOT, **kwargs) -> dict:
    return run_per_stock_etl(
        "fetch_holder_number",
        token,
        fetch_holder_number,
        convert_tushare_holder_number,
        output_root=output_root,
        raw_output_root=raw_output_root,
        clip_start_to_list_date=False,
        **kwargs,
    )


def main() -> int:
    args = parse_args()
    if not require_token(args):
        return 2
    return run_main(
        "fetch_holder_number",
        lambda: run_holder_number_etl(
            token=args.token,
            output_root=args.output_root,
            raw_output_root=args.raw_output_root,
            write_raw=args.with_raw,
            **stock_selection_kwargs(args),
            **run_control_kwargs(args),
        ),
        unit="stocks",
    )


if __name__ == "__main__":
    raise SystemExit(main())
