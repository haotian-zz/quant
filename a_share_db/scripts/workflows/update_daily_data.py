#!/usr/bin/env python3
"""One-command daily database update.

Default behavior:
- update daily/none for all listed stocks
- update adj_factor for all listed stocks
- incrementally merge daily/hfq missing rows
- do not rebuild daily/qfq
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.commands import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_PROGRESS_EVERY,
    DEFAULT_REQUEST_INTERVAL,
    DEFAULT_RETRY_INTERVAL,
)
from a_share_db.constant.paths import BACKUP_ROOT
from a_share_db.scripts.market.update_daily import run_update_daily


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="One-command daily update for none daily, adj_factor, and hfq."
    )
    parser.add_argument(
        "--token",
        default=os.getenv("TUSHARE_TOKEN"),
        help="Tushare token. Defaults to env var TUSHARE_TOKEN.",
    )
    parser.add_argument(
        "--end-date",
        default=datetime.now().strftime("%Y%m%d"),
        help="Update end date in YYYYMMDD format. Default: today.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and merge dataframes, but do not write CSV files or logs.",
    )
    parser.add_argument(
        "--request-interval",
        type=float,
        default=DEFAULT_REQUEST_INTERVAL,
        help=f"Seconds to sleep between Tushare requests. Default: {DEFAULT_REQUEST_INTERVAL}.",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=DEFAULT_PROGRESS_EVERY,
        help=f"Print progress every N stocks. Default: {DEFAULT_PROGRESS_EVERY}.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=DEFAULT_MAX_RETRIES,
        help=f"Maximum attempts per stock request. Default: {DEFAULT_MAX_RETRIES}.",
    )
    parser.add_argument(
        "--retry-interval",
        type=float,
        default=DEFAULT_RETRY_INTERVAL,
        help=f"Seconds to sleep between retries. Default: {DEFAULT_RETRY_INTERVAL}.",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop immediately when one stock fails instead of continuing.",
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
        # This is the routine daily command; detailed options stay in update_daily.py.
        result = run_update_daily(
            token=args.token,
            all_stocks=True,
            end_date=args.end_date,
            adjust_types=["hfq"],
            update_adj_factor=True,
            rebuild_adjusted=True,
            dry_run=args.dry_run,
            request_interval=args.request_interval,
            progress_every=args.progress_every,
            max_retries=args.max_retries,
            retry_interval=args.retry_interval,
            stop_on_error=args.stop_on_error,
            backup_root=args.backup_root,
            create_backup=args.create_backup,
        )
    except Exception as exc:
        print(f"update_daily_data failed: {exc}", file=sys.stderr)
        return 1

    action = "Dry run updated" if args.dry_run else "Updated"
    print(
        f"{action} {result['updated_count']} of {result['stock_count']} stocks "
        f"through {result['end_date']} "
        f"({result['skipped_count']} skipped, {result['missing_count']} missing, "
        f"{result['failure_count']} failed)."
    )
    print(
        f"New rows: daily={result['daily_new_rows']}, "
        f"adj_factor={result['adj_factor_new_rows']}, "
        f"adjusted_rows={result['adjusted_rows']}."
    )
    if result["failures"]:
        print("Failures:", file=sys.stderr)
        for item in result["failures"][:20]:
            print(f"  {item['code']} ({item['ts_code']}): {item['error']}", file=sys.stderr)
        if len(result["failures"]) > 20:
            print(f"  ... {len(result['failures']) - 20} more", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
