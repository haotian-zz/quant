#!/usr/bin/env python3
"""Fetch top-10 shareholders and top-10 float shareholders by report period from Tushare.

Outputs:
data/financial/top10_holders/{period}.csv        (top10_holders)
data/financial/top10_float_holders/{period}.csv  (top10_floatholders)
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.holders import (
    DEFAULT_HOLDER_START_DATE,
    TOP10_HOLDER_COLUMNS,
    TOP10_HOLDER_PAGE_SIZE,
    TUSHARE_TOP10_HOLDER_FIELDS,
)
from a_share_db.constant.paths import RAW_TUSHARE_ROOT, TOP10_FLOAT_HOLDERS_ROOT, TOP10_HOLDERS_ROOT
from a_share_db.utils.cli import (
    add_date_range_arguments,
    add_run_control_arguments,
    add_token_argument,
    report_result,
    require_token,
    run_control_kwargs,
)
from a_share_db.utils.etl_common import convert_mapped_frame, fetch_paginated, iter_report_periods
from a_share_db.utils.etl_runners import run_per_key_etl


FIELD_MAP = dict(zip(TUSHARE_TOP10_HOLDER_FIELDS, TOP10_HOLDER_COLUMNS))
HOLDER_TABLES = {
    "holders": ("top10_holders", TOP10_HOLDERS_ROOT),
    "float_holders": ("top10_floatholders", TOP10_FLOAT_HOLDERS_ROOT),
}
DEFAULT_REFRESH_RECENT_DAYS = 400


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Tushare top10_holders / top10_floatholders by report period."
    )
    add_token_argument(parser)
    parser.add_argument("--tables", nargs="+", choices=list(HOLDER_TABLES), default=list(HOLDER_TABLES), help="Tables to fetch. Default: holders float_holders.")
    parser.add_argument("--periods", nargs="+", help="Explicit report periods in YYYYMMDD format.")
    add_date_range_arguments(parser, default_start=DEFAULT_HOLDER_START_DATE, end_defaults_to_today=True)
    parser.add_argument("--refresh-recent-days", type=int, default=DEFAULT_REFRESH_RECENT_DAYS, help=f"With --resume, periods ending within this many days are always re-fetched. Default: {DEFAULT_REFRESH_RECENT_DAYS}.")
    parser.add_argument("--with-raw", action="store_true", help="Also write raw provider CSV files under data/raw/tushare/.")
    add_run_control_arguments(parser)
    return parser.parse_args()


def convert_tushare_top10_holders(raw, period: str | None = None):
    """Convert raw Tushare top10 holder rows into the local top10 holder schema."""
    frame = convert_mapped_frame(
        raw,
        FIELD_MAP,
        TOP10_HOLDER_COLUMNS,
        sort_columns=["code", "report_period", "announce_date", "holder_name"],
        date_columns=["announce_date", "report_period"],
    )
    return frame.drop_duplicates(subset=["code", "report_period", "announce_date", "holder_name"], keep="last").reset_index(drop=True)


def run_top10_holders_etl(
    table: str,
    token: str,
    periods=None,
    start_date: str | None = None,
    end_date: str | None = None,
    refresh_recent_days: int = DEFAULT_REFRESH_RECENT_DAYS,
    **kwargs,
) -> dict:
    api_name, output_root = HOLDER_TABLES[table]
    selected_periods = list(periods) if periods else iter_report_periods(start_date or DEFAULT_HOLDER_START_DATE, end_date)
    cutoff = (datetime.now() - timedelta(days=refresh_recent_days)).strftime("%Y%m%d")
    request_interval = kwargs.get("request_interval", 0.0)

    def fetch_fn(pro, period: str):
        return fetch_paginated(pro, api_name, TUSHARE_TOP10_HOLDER_FIELDS, page_size=TOP10_HOLDER_PAGE_SIZE, request_interval=request_interval, period=period)

    return run_per_key_etl(
        f"fetch_top10_{table}",
        token,
        keys=selected_periods,
        fetch_fn=fetch_fn,
        convert_fn=convert_tushare_top10_holders,
        output_path_fn=lambda period: Path(output_root) / f"{period}.csv",
        raw_output_path_fn=lambda period: RAW_TUSHARE_ROOT / f"top10_{table}" / f"{period}.csv",
        # Recent periods keep receiving filings, so they are re-fetched under --resume.
        resume_skip_fn=lambda period, path: period < cutoff and path.exists() and path.stat().st_size > 0,
        **kwargs,
    )


def main() -> int:
    args = parse_args()
    if not require_token(args):
        return 2
    exit_code = 0
    for table in args.tables:
        try:
            result = run_top10_holders_etl(
                table,
                token=args.token,
                periods=args.periods,
                start_date=args.start_date,
                end_date=args.end_date,
                refresh_recent_days=args.refresh_recent_days,
                write_raw=args.with_raw,
                **run_control_kwargs(args),
            )
        except Exception as exc:
            print(f"fetch_top10_{table} failed: {exc}", file=sys.stderr)
            exit_code = 1
            continue
        exit_code = max(exit_code, report_result(result, f"fetch_top10_{table}", unit="periods"))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
