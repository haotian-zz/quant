"""Shared argparse building blocks for fetch scripts.

Every fetch command exposes the same operational flags (token, dry-run,
resume, rate limiting, retries, logging, backup). Keeping them here means a
new table script only declares what is specific to that table.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

from a_share_db.constant.commands import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_PROGRESS_EVERY,
    DEFAULT_REQUEST_INTERVAL,
    DEFAULT_RETRY_INTERVAL,
)
from a_share_db.constant.paths import BACKUP_ROOT, STOCK_BASIC_PATH, TRADE_CALENDAR_PATH
from a_share_db.utils.etl_common import DEFAULT_STOCK_STATUSES


def today_provider_date() -> str:
    return datetime.now().strftime("%Y%m%d")


def add_token_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--token",
        default=os.getenv("TUSHARE_TOKEN"),
        help="Tushare token. Defaults to env var TUSHARE_TOKEN.",
    )


def add_stock_selection_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--codes", nargs="+", help="Local 6-digit stock codes, for example 600519 000001.")
    parser.add_argument("--codes-file", type=Path, help="Text file with one local 6-digit stock code per line.")
    parser.add_argument("--all-stocks", action="store_true", help="Fetch every selected-status stock in stock_basic.csv.")
    parser.add_argument(
        "--stock-basic",
        type=Path,
        default=STOCK_BASIC_PATH,
        help=f"Local stock_basic.csv path. Default: {STOCK_BASIC_PATH}",
    )
    parser.add_argument(
        "--statuses",
        nargs="+",
        default=list(DEFAULT_STOCK_STATUSES),
        help="Local stock_basic status values to include (listed delisted suspended approved, or all). Default: listed.",
    )
    parser.add_argument("--limit-stocks", type=int, help="Fetch only the first N selected stocks. Useful for smoke tests.")


def add_date_range_arguments(
    parser: argparse.ArgumentParser,
    default_start: str | None = None,
    default_end: str | None = None,
    end_defaults_to_today: bool = False,
) -> None:
    parser.add_argument(
        "--start-date",
        default=default_start,
        help=f"Start date in YYYYMMDD format. Default: {default_start or 'provider behavior'}.",
    )
    parser.add_argument(
        "--end-date",
        default=today_provider_date() if end_defaults_to_today else default_end,
        help="End date in YYYYMMDD format. Default: " + ("today." if end_defaults_to_today else f"{default_end or 'provider behavior'}."),
    )


def add_calendar_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--trade-calendar",
        type=Path,
        default=TRADE_CALENDAR_PATH,
        help=f"Local trade_calendar.csv path. Default: {TRADE_CALENDAR_PATH}",
    )
    parser.add_argument("--limit-days", type=int, help="Fetch only the first N trading days. Useful for smoke tests.")


def add_output_arguments(
    parser: argparse.ArgumentParser,
    default_output: Path,
    default_raw_output: Path | None = None,
    output_is_dir: bool = True,
) -> None:
    label = "Output directory" if output_is_dir else "Output CSV path"
    parser.add_argument("--output-root" if output_is_dir else "--output", type=Path, default=default_output, help=f"{label}. Default: {default_output}")
    if default_raw_output is not None:
        parser.add_argument(
            "--raw-output-root" if output_is_dir else "--raw-output",
            type=Path,
            default=default_raw_output,
            help=f"Raw provider output when --with-raw is set. Default: {default_raw_output}",
        )
        parser.add_argument("--with-raw", action="store_true", help="Also write raw provider CSV files.")


def add_run_control_arguments(parser: argparse.ArgumentParser, resumable: bool = True, loops: bool = True) -> None:
    parser.add_argument("--dry-run", action="store_true", help="Fetch and convert data, but do not write CSV files or logs.")
    if resumable:
        parser.add_argument("--resume", action="store_true", help="Skip outputs that already exist and are non-empty.")
    if loops:
        parser.add_argument(
            "--request-interval",
            type=float,
            default=DEFAULT_REQUEST_INTERVAL,
            help=f"Seconds to sleep between provider requests. Default: {DEFAULT_REQUEST_INTERVAL}.",
        )
        parser.add_argument(
            "--progress-every",
            type=int,
            default=DEFAULT_PROGRESS_EVERY,
            help=f"Print progress every N items. Use 0 to disable. Default: {DEFAULT_PROGRESS_EVERY}.",
        )
        parser.add_argument("--stop-on-error", action="store_true", help="Stop immediately on the first failure instead of continuing.")
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES, help=f"Maximum attempts per request. Default: {DEFAULT_MAX_RETRIES}.")
    parser.add_argument("--retry-interval", type=float, default=DEFAULT_RETRY_INTERVAL, help=f"Seconds to sleep between retries. Default: {DEFAULT_RETRY_INTERVAL}.")
    parser.add_argument("--no-log", action="store_true", help="Do not append execution status to data/logs/etl_log.csv.")
    parser.add_argument("--backup-root", type=Path, default=BACKUP_ROOT, help=f"Backup directory for existing files. Default: {BACKUP_ROOT}")
    parser.add_argument("--backup", dest="create_backup", action="store_true", help="Move existing output files to backups before replacing them. Default: off.")
    parser.add_argument("--no-backup", dest="create_backup", action="store_false", help=argparse.SUPPRESS)
    parser.set_defaults(create_backup=False)


def require_token(args: argparse.Namespace) -> bool:
    if not args.token:
        print("Tushare token is required. Set TUSHARE_TOKEN or pass --token.", file=sys.stderr)
        return False
    return True


def run_control_kwargs(args: argparse.Namespace) -> dict:
    """Translate common flags into runner keyword arguments."""
    kwargs = {
        "dry_run": args.dry_run,
        "write_log": not args.no_log,
        "backup_root": args.backup_root,
        "create_backup": args.create_backup,
        "max_retries": args.max_retries,
        "retry_interval": args.retry_interval,
    }
    for name in ("resume", "request_interval", "progress_every", "stop_on_error"):
        if hasattr(args, name):
            kwargs[name] = getattr(args, name)
    return kwargs


def stock_selection_kwargs(args: argparse.Namespace) -> dict:
    return {
        "codes": args.codes,
        "codes_file": args.codes_file,
        "all_stocks": args.all_stocks,
        "stock_basic_path": args.stock_basic,
        "statuses": args.statuses,
        "limit_stocks": args.limit_stocks,
    }


def report_result(result: dict, script_name: str, unit: str = "items") -> int:
    """Print a summary in the same style as the first-generation scripts."""
    action = "Dry run converted" if result.get("dry_run") else "Wrote"
    count_key = next((key for key in ("stock_count", "day_count", "key_count") if key in result), None)
    count_text = f" for {result[count_key]} {unit}" if count_key else ""
    target = result.get("output_root") or result.get("output") or ""
    target_text = f" to {target}" if target and not result.get("dry_run") else ""
    print(
        f"{action} {result['row_count']} rows{count_text}{target_text} "
        f"({result['skipped_count']} skipped, {result['failure_count']} failed)."
    )
    for backup_path in result.get("backup_paths", []):
        print(f"Backed up previous file to {backup_path}")
    if result["failures"]:
        print("Failures:", file=sys.stderr)
        for item in result["failures"][:20]:
            print(f"  {item['item']}: {item['error']}", file=sys.stderr)
        if len(result["failures"]) > 20:
            print(f"  ... {len(result['failures']) - 20} more", file=sys.stderr)
        return 1
    return 0


def run_main(script_name: str, runner, unit: str = "items") -> int:
    """Standard main wrapper: run, report, and map exceptions to exit codes."""
    try:
        result = runner()
    except Exception as exc:
        print(f"{script_name} failed: {exc}", file=sys.stderr)
        return 1
    return report_result(result, script_name, unit)
