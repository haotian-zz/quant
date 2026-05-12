#!/usr/bin/env python3
"""One-command refresh for stock_basic and trade_calendar metadata."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.commands import DEFAULT_TRADE_CALENDAR_START_DATE
from a_share_db.constant.paths import BACKUP_ROOT
from a_share_db.constant.stock_basic import DEFAULT_TUSHARE_LIST_STATUSES
from a_share_db.constant.trade_calendar import DEFAULT_A_SHARE_EXCHANGES
from a_share_db.scripts.metadata.fetch_stock_basic import run_stock_basic_etl
from a_share_db.scripts.metadata.fetch_trade_calendar import run_trade_calendar_etl


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="One-command refresh for stock_basic and trade_calendar."
    )
    parser.add_argument(
        "--token",
        default=os.getenv("TUSHARE_TOKEN"),
        help="Tushare token. Defaults to env var TUSHARE_TOKEN.",
    )
    parser.add_argument(
        "--calendar-start-date",
        default=DEFAULT_TRADE_CALENDAR_START_DATE,
        help=f"Trade calendar start date in YYYYMMDD format. Default: {DEFAULT_TRADE_CALENDAR_START_DATE}.",
    )
    parser.add_argument(
        "--calendar-end-date",
        default=datetime.now().strftime("%Y%m%d"),
        help="Trade calendar end date in YYYYMMDD format. Default: today.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and convert data, but do not write CSV files or logs.",
    )
    parser.add_argument(
        "--with-raw",
        action="store_true",
        help="Also write raw Tushare metadata CSV files.",
    )
    parser.add_argument(
        "--backup",
        dest="create_backup",
        action="store_true",
        help="Move existing output files to backups before replacing them. Default: off.",
    )
    parser.add_argument(
        "--backup-root",
        type=Path,
        default=BACKUP_ROOT,
        help=f"Backup directory for existing CSV files. Default: {BACKUP_ROOT}.",
    )
    parser.set_defaults(create_backup=False)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.token:
        print("Tushare token is required. Set TUSHARE_TOKEN or pass --token.", file=sys.stderr)
        return 2

    try:
        # This wrapper only supplies project defaults; real ETL logic stays importable.
        stock_result = run_stock_basic_etl(
            token=args.token,
            statuses=DEFAULT_TUSHARE_LIST_STATUSES,
            write_raw=args.with_raw,
            dry_run=args.dry_run,
            backup_root=args.backup_root,
            create_backup=args.create_backup,
        )
        calendar_result = run_trade_calendar_etl(
            token=args.token,
            exchanges=DEFAULT_A_SHARE_EXCHANGES,
            start_date=args.calendar_start_date,
            end_date=args.calendar_end_date,
            write_raw=args.with_raw,
            dry_run=args.dry_run,
            backup_root=args.backup_root,
            create_backup=args.create_backup,
        )
    except Exception as exc:
        print(f"refresh_metadata failed: {exc}", file=sys.stderr)
        return 1

    action = "Dry run refreshed" if args.dry_run else "Refreshed"
    print(
        f"{action} stock_basic rows={stock_result['row_count']} "
        f"and trade_calendar rows={calendar_result['row_count']}."
    )
    if stock_result["status"] != "success" or calendar_result["status"] != "success":
        print(
            f"stock_basic status={stock_result['status']} error={stock_result['error_message']}",
            file=sys.stderr,
        )
        print(
            f"trade_calendar status={calendar_result['status']} error={calendar_result['error_message']}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
