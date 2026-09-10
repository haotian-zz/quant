#!/usr/bin/env python3
"""Fetch the full A-share stock name history from Tushare.

Outputs:
data/metadata/stock_name_history.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.name_change import (
    NAME_CHANGE_PAGE_SIZE,
    STOCK_NAME_HISTORY_COLUMNS,
    TUSHARE_NAME_CHANGE_FIELDS,
)
from a_share_db.constant.paths import RAW_TUSHARE_ROOT, STOCK_NAME_HISTORY_PATH
from a_share_db.utils.cli import (
    add_output_arguments,
    add_run_control_arguments,
    add_token_argument,
    require_token,
    run_control_kwargs,
    run_main,
)
from a_share_db.utils.etl_common import convert_mapped_frame, fetch_paginated
from a_share_db.utils.etl_runners import run_single_table_etl


DEFAULT_OUTPUT = STOCK_NAME_HISTORY_PATH
DEFAULT_RAW_OUTPUT = RAW_TUSHARE_ROOT / "stock_name_history.csv"
FIELD_MAP = dict(zip(TUSHARE_NAME_CHANGE_FIELDS, STOCK_NAME_HISTORY_COLUMNS))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Tushare namechange data and build data/metadata/stock_name_history.csv."
    )
    add_token_argument(parser)
    add_output_arguments(parser, DEFAULT_OUTPUT, DEFAULT_RAW_OUTPUT, output_is_dir=False)
    parser.add_argument("--limit", type=int, help="Write only the first N normalized rows. Useful for smoke tests.")
    add_run_control_arguments(parser, resumable=False, loops=False)
    return parser.parse_args()


def fetch_name_change(pro):
    # The whole market fits in two pages; no per-stock loop is needed.
    frame = fetch_paginated(pro, "namechange", TUSHARE_NAME_CHANGE_FIELDS, page_size=NAME_CHANGE_PAGE_SIZE)
    return frame.drop_duplicates(subset=["ts_code", "name", "start_date"], keep="last")


def convert_tushare_name_change(raw):
    """Convert raw Tushare namechange rows into the local stock_name_history schema."""
    return convert_mapped_frame(
        raw,
        FIELD_MAP,
        STOCK_NAME_HISTORY_COLUMNS,
        sort_columns=["code", "start_date"],
        date_columns=["start_date", "end_date", "announce_date"],
    )


def run_name_change_etl(token: str, output_path: Path = DEFAULT_OUTPUT, raw_output_path: Path = DEFAULT_RAW_OUTPUT, **kwargs) -> dict:
    return run_single_table_etl(
        "fetch_name_change",
        token,
        fetch_name_change,
        convert_tushare_name_change,
        output_path=output_path,
        raw_output_path=raw_output_path,
        **kwargs,
    )


def main() -> int:
    args = parse_args()
    if not require_token(args):
        return 2
    return run_main(
        "fetch_name_change",
        lambda: run_name_change_etl(
            token=args.token,
            output_path=args.output,
            raw_output_path=args.raw_output,
            write_raw=args.with_raw,
            limit=args.limit,
            **run_control_kwargs(args),
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())
