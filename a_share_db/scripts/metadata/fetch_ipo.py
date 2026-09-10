#!/usr/bin/env python3
"""Fetch the A-share IPO list from Tushare.

Outputs:
data/metadata/ipo.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.ipo import (
    DEFAULT_IPO_START_DATE,
    IPO_COLUMNS,
    IPO_PAGE_SIZE,
    TUSHARE_IPO_FUNDS_TO_LOCAL,
    TUSHARE_IPO_SHARE_TO_LOCAL,
    TUSHARE_NEW_SHARE_FIELDS,
)
from a_share_db.constant.paths import IPO_PATH, RAW_TUSHARE_ROOT
from a_share_db.utils.cli import (
    add_date_range_arguments,
    add_output_arguments,
    add_run_control_arguments,
    add_token_argument,
    require_token,
    run_control_kwargs,
    run_main,
)
from a_share_db.utils.etl_common import convert_mapped_frame, fetch_paginated
from a_share_db.utils.etl_runners import run_single_table_etl


DEFAULT_OUTPUT = IPO_PATH
DEFAULT_RAW_OUTPUT = RAW_TUSHARE_ROOT / "ipo.csv"
FIELD_MAP = dict(zip(TUSHARE_NEW_SHARE_FIELDS, IPO_COLUMNS))
SCALES = {
    "amount": TUSHARE_IPO_SHARE_TO_LOCAL,
    "market_amount": TUSHARE_IPO_SHARE_TO_LOCAL,
    "limit_amount": TUSHARE_IPO_SHARE_TO_LOCAL,
    "funds": TUSHARE_IPO_FUNDS_TO_LOCAL,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Tushare new_share data and build data/metadata/ipo.csv.")
    add_token_argument(parser)
    add_date_range_arguments(parser, default_start=DEFAULT_IPO_START_DATE, end_defaults_to_today=True)
    add_output_arguments(parser, DEFAULT_OUTPUT, DEFAULT_RAW_OUTPUT, output_is_dir=False)
    parser.add_argument("--limit", type=int, help="Write only the first N normalized rows. Useful for smoke tests.")
    add_run_control_arguments(parser, resumable=False, loops=False)
    return parser.parse_args()


def build_fetcher(start_date: str | None, end_date: str | None):
    def fetch_ipo(pro):
        return fetch_paginated(
            pro,
            "new_share",
            TUSHARE_NEW_SHARE_FIELDS,
            page_size=IPO_PAGE_SIZE,
            start_date=start_date,
            end_date=end_date,
        ).drop_duplicates(subset=["ts_code"], keep="last")

    return fetch_ipo


def convert_tushare_ipo(raw):
    """Convert raw Tushare new_share rows into the local ipo schema."""
    return convert_mapped_frame(
        raw,
        FIELD_MAP,
        IPO_COLUMNS,
        sort_columns=["ipo_date", "code"],
        date_columns=["ipo_date", "list_date"],
        scales=SCALES,
    )


def run_ipo_etl(token: str, start_date: str | None = None, end_date: str | None = None, output_path: Path = DEFAULT_OUTPUT, raw_output_path: Path = DEFAULT_RAW_OUTPUT, **kwargs) -> dict:
    return run_single_table_etl(
        "fetch_ipo",
        token,
        build_fetcher(start_date, end_date),
        convert_tushare_ipo,
        output_path=output_path,
        raw_output_path=raw_output_path,
        **kwargs,
    )


def main() -> int:
    args = parse_args()
    if not require_token(args):
        return 2
    return run_main(
        "fetch_ipo",
        lambda: run_ipo_etl(
            token=args.token,
            start_date=args.start_date,
            end_date=args.end_date,
            output_path=args.output,
            raw_output_path=args.raw_output,
            write_raw=args.with_raw,
            limit=args.limit,
            **run_control_kwargs(args),
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())
