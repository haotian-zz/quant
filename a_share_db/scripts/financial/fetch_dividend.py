#!/usr/bin/env python3
"""Fetch dividend and share distribution history per stock from Tushare.

Outputs:
data/financial/dividend/{code}.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.financial import (
    DIVIDEND_COLUMNS,
    DIVIDEND_PAGE_SIZE,
    TUSHARE_DIVIDEND_FIELD_MAP,
    TUSHARE_DIVIDEND_FIELDS,
    TUSHARE_DIVIDEND_SHARE_TO_LOCAL,
)
from a_share_db.constant.paths import DIVIDEND_ROOT, RAW_TUSHARE_ROOT
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


DEFAULT_OUTPUT_ROOT = DIVIDEND_ROOT
DEFAULT_RAW_OUTPUT_ROOT = RAW_TUSHARE_ROOT / "dividend"
DATE_COLUMNS = [
    "report_period",
    "announce_date",
    "record_date",
    "ex_dividend_date",
    "pay_date",
    "share_listing_date",
    "implementation_announce_date",
    "base_date",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Tushare dividend data and build data/financial/dividend/{code}.csv.")
    add_token_argument(parser)
    add_stock_selection_arguments(parser)
    add_output_arguments(parser, DEFAULT_OUTPUT_ROOT, DEFAULT_RAW_OUTPUT_ROOT)
    add_run_control_arguments(parser)
    return parser.parse_args()


def fetch_dividend(pro, ts_code: str, stock: dict, start_date: str | None, end_date: str | None):
    # dividend has no date-range filter; the full per-stock history is small.
    return fetch_paginated(pro, "dividend", TUSHARE_DIVIDEND_FIELDS, page_size=DIVIDEND_PAGE_SIZE, ts_code=ts_code)


def convert_tushare_dividend(raw, stock: dict | None = None):
    """Convert raw Tushare dividend rows into the local dividend schema."""
    frame = convert_mapped_frame(
        raw,
        TUSHARE_DIVIDEND_FIELD_MAP,
        DIVIDEND_COLUMNS,
        sort_columns=["code", "report_period", "announce_date", "process"],
        date_columns=DATE_COLUMNS,
        scales={"base_share": TUSHARE_DIVIDEND_SHARE_TO_LOCAL},
    )
    # Announcements progress through 预案 -> 股东大会通过 -> 实施; keep each stage row once.
    return frame.drop_duplicates(subset=["code", "report_period", "announce_date", "process"], keep="last").reset_index(drop=True)


def run_dividend_etl(token: str, output_root: Path = DEFAULT_OUTPUT_ROOT, raw_output_root: Path = DEFAULT_RAW_OUTPUT_ROOT, **kwargs) -> dict:
    return run_per_stock_etl(
        "fetch_dividend",
        token,
        fetch_dividend,
        convert_tushare_dividend,
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
        "fetch_dividend",
        lambda: run_dividend_etl(
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
