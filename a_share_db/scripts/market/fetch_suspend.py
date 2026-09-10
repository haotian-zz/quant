#!/usr/bin/env python3
"""Fetch A-share suspension/resumption records from Tushare by trade date.

Outputs:
data/market_data/suspend/{year}.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.paths import RAW_TUSHARE_ROOT, SUSPEND_ROOT
from a_share_db.constant.suspend import (
    DEFAULT_SUSPEND_START_DATE,
    SUSPEND_COLUMNS,
    TUSHARE_SUSPEND_FIELDS,
    TUSHARE_SUSPEND_TYPE_MAP,
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


DEFAULT_OUTPUT_ROOT = SUSPEND_ROOT
DEFAULT_RAW_OUTPUT_ROOT = RAW_TUSHARE_ROOT / "suspend"
FIELD_MAP = dict(zip(TUSHARE_SUSPEND_FIELDS, SUSPEND_COLUMNS))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Tushare suspend_d data by trade date and build data/market_data/suspend/{year}.csv."
    )
    add_token_argument(parser)
    add_date_range_arguments(parser, default_start=DEFAULT_SUSPEND_START_DATE, end_defaults_to_today=True)
    add_calendar_arguments(parser)
    add_output_arguments(parser, DEFAULT_OUTPUT_ROOT, DEFAULT_RAW_OUTPUT_ROOT)
    add_run_control_arguments(parser)
    return parser.parse_args()


def fetch_suspend(pro, trade_date: str):
    # Per-stock suspend_d queries are truncated by the provider, so fetch by day.
    return fetch_paginated(pro, "suspend_d", TUSHARE_SUSPEND_FIELDS, trade_date=trade_date)


def convert_tushare_suspend(raw):
    """Convert raw Tushare suspend_d rows into the local suspend schema."""
    return convert_mapped_frame(
        raw,
        FIELD_MAP,
        SUSPEND_COLUMNS,
        sort_columns=["trade_date", "code"],
        date_columns=["trade_date"],
        value_maps={"suspend_type": TUSHARE_SUSPEND_TYPE_MAP},
    )


def run_suspend_etl(token: str, output_root: Path = DEFAULT_OUTPUT_ROOT, raw_output_root: Path = DEFAULT_RAW_OUTPUT_ROOT, start_date: str | None = None, **kwargs) -> dict:
    # Importers may omit the start date; fall back to the provider coverage start.
    kwargs["start_date"] = start_date or DEFAULT_SUSPEND_START_DATE
    return run_per_date_etl(
        "fetch_suspend",
        token,
        fetch_suspend,
        convert_tushare_suspend,
        output_root=output_root,
        raw_output_root=raw_output_root,
        **kwargs,
    )


def main() -> int:
    args = parse_args()
    if not require_token(args):
        return 2
    return run_main(
        "fetch_suspend",
        lambda: run_suspend_etl(
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
