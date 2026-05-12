#!/usr/bin/env python3
"""One-command rebuild for adjusted daily tables."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.commands import DEFAULT_PROGRESS_EVERY
from a_share_db.constant.paths import BACKUP_ROOT
from a_share_db.scripts.market.build_adjusted_daily import ADJUSTED_TYPES, run_build_adjusted_daily


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="One-command rebuild for qfq/hfq adjusted daily tables."
    )
    parser.add_argument(
        "--adjust-types",
        nargs="+",
        choices=ADJUSTED_TYPES,
        default=ADJUSTED_TYPES,
        help="Adjusted price types to rebuild. Default: qfq hfq.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build dataframes, but do not write CSV files or logs.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip adjusted files that already exist and are non-empty.",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=DEFAULT_PROGRESS_EVERY,
        help=f"Print progress every N stocks. Default: {DEFAULT_PROGRESS_EVERY}.",
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
    try:
        # This wrapper rebuilds adjusted tables with project defaults.
        result = run_build_adjusted_daily(
            all_stocks=True,
            adjust_types=args.adjust_types,
            dry_run=args.dry_run,
            resume=args.resume,
            progress_every=args.progress_every,
            stop_on_error=args.stop_on_error,
            backup_root=args.backup_root,
            create_backup=args.create_backup,
        )
    except Exception as exc:
        print(f"rebuild_adjusted_daily_data failed: {exc}", file=sys.stderr)
        return 1

    action = "Dry run rebuilt" if args.dry_run else "Rebuilt"
    print(
        f"{action} {result['row_count']} rows for {result['stock_count']} stocks "
        f"({result['skipped_count']} skipped, {result['failure_count']} failed)."
    )
    if result["failures"]:
        print("Failures:", file=sys.stderr)
        for item in result["failures"][:20]:
            print(f"  {item['code']}: {item['error']}", file=sys.stderr)
        if len(result["failures"]) > 20:
            print(f"  ... {len(result['failures']) - 20} more", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
