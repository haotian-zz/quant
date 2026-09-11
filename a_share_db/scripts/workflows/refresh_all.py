#!/usr/bin/env python3
"""One-command routine refresh of the whole warehouse.

Steps, in order:
1. daily/none, adj_factor and hfq            (update_daily_data)
2. daily_basic                               (update_daily_basic)
3. every second-generation table             (build_extended_history --update)
4. stock index futures                       (fetch_futures, active contracts + continuous series)
5. minute bars, optional                     (fetch_minute --update)
6. 15m/30m/60m none/hfq from 5m, optional    (build_minute_derived --update; qfq needs a full rebuild)
7. Parquet for everything except minute      (build_parquet)

The command exits early on non-trading days unless --force is given, so it
can be scheduled every evening with cron or launchd. Each step continues after
failures; the final summary lists what to rerun.
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

from a_share_db.constant.commands import DEFAULT_MAX_RETRIES, DEFAULT_PROGRESS_EVERY, DEFAULT_REQUEST_INTERVAL, DEFAULT_RETRY_INTERVAL
from a_share_db.constant.minute import MINUTE_FREQUENCIES
from a_share_db.constant.futures import DEFAULT_INDEX_FUTURES_PRODUCTS
from a_share_db.constant.paths import FUTURES_BASIC_PATH, TRADE_CALENDAR_PATH
from a_share_db.scripts.futures.fetch_futures import load_contract_codes, run_futures_basic_etl, run_futures_daily_etl, run_futures_mapping_etl
from a_share_db.scripts.market.build_minute_derived import run_build_minute_derived
from a_share_db.scripts.market.fetch_minute import run_minute_etl
from a_share_db.scripts.market.update_daily import run_update_daily
from a_share_db.scripts.market.update_daily_basic import run_update_daily_basic
from a_share_db.scripts.warehouse.build_parquet import run_build_parquet
from a_share_db.scripts.workflows import build_extended_history
from a_share_db.utils.etl_common import parse_date_arg, read_trading_days


PARQUET_TABLES_FOR_REFRESH = ["metadata", "daily", "adj_factor", "daily_basic", "extended", "futures"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Routine refresh: prices, indicators, extended tables, minute bars, Parquet.")
    parser.add_argument("--token", default=os.getenv("TUSHARE_TOKEN"), help="Tushare token. Defaults to env var TUSHARE_TOKEN.")
    parser.add_argument("--end-date", default=datetime.now().strftime("%Y%m%d"), help="Refresh through this date in YYYYMMDD format. Default: today.")
    parser.add_argument("--force", action="store_true", help="Run even when --end-date is not a trading day.")
    parser.add_argument("--skip-minute", action="store_true", help="Do not update minute bars.")
    parser.add_argument("--minute-frequencies", nargs="+", choices=MINUTE_FREQUENCIES, default=["1m", "5m"], help="Minute frequencies to update. Default: 1m 5m.")
    parser.add_argument("--skip-parquet", action="store_true", help="Do not rebuild Parquet.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and convert data, but do not write CSV files or logs.")
    parser.add_argument("--request-interval", type=float, default=DEFAULT_REQUEST_INTERVAL, help=f"Seconds between provider requests. Default: {DEFAULT_REQUEST_INTERVAL}.")
    parser.add_argument("--progress-every", type=int, default=DEFAULT_PROGRESS_EVERY, help=f"Print progress every N items. Default: {DEFAULT_PROGRESS_EVERY}.")
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES, help=f"Maximum attempts per request. Default: {DEFAULT_MAX_RETRIES}.")
    parser.add_argument("--retry-interval", type=float, default=DEFAULT_RETRY_INTERVAL, help=f"Seconds between retries. Default: {DEFAULT_RETRY_INTERVAL}.")
    return parser.parse_args()


def is_trading_day(end_date: str) -> bool:
    day = parse_date_arg(end_date)
    return bool(read_trading_days(TRADE_CALENDAR_PATH, day, day, "SSE"))


def main() -> int:
    args = parse_args()
    if not args.token:
        print("Tushare token is required. Set TUSHARE_TOKEN or pass --token.", file=sys.stderr)
        return 2
    if not args.force and not is_trading_day(args.end_date):
        print(f"{args.end_date} is not a trading day; nothing to refresh (use --force to override).")
        return 0

    loop = {
        "dry_run": args.dry_run,
        "request_interval": args.request_interval,
        "progress_every": args.progress_every,
        "max_retries": args.max_retries,
        "retry_interval": args.retry_interval,
    }
    steps = [
        ("update_daily", lambda: run_update_daily(args.token, all_stocks=True, end_date=args.end_date, adjust_types=["hfq"], **loop)),
        ("update_daily_basic", lambda: run_update_daily_basic(args.token, all_stocks=True, end_date=args.end_date, **loop)),
        ("extended_tables", lambda: run_extended_update(args)),
    ]
    steps.append(("futures", lambda: run_futures_refresh(args, loop)))
    if not args.skip_minute:
        steps.append(
            (
                "minute",
                lambda: run_minute_etl(
                    args.token,
                    all_stocks=True,
                    frequencies=args.minute_frequencies,
                    start_date="20100101",
                    end_date=args.end_date,
                    update=True,
                    **loop,
                ),
            )
        )
    if not args.skip_minute and "5m" in args.minute_frequencies:
        steps.append(
            (
                "minute_derived",
                lambda: run_build_minute_derived(
                    all_stocks=True,
                    source_frequency="5m",
                    frequencies=["15m", "30m", "60m"],
                    adjust_types=["none", "hfq"],
                    incremental=True,
                    dry_run=args.dry_run,
                    progress_every=args.progress_every,
                ),
            )
        )
    if not args.skip_parquet:
        steps.append(("parquet", lambda: run_build_parquet(tables=PARQUET_TABLES_FOR_REFRESH, dry_run=args.dry_run, progress_every=5000)))

    failures = []
    for name, step in steps:
        print(f"[{datetime.now():%H:%M:%S}] {name} started", flush=True)
        try:
            result = step()
        except Exception as exc:
            failures.append((name, str(exc)))
            print(f"[{datetime.now():%H:%M:%S}] {name} FAILED: {exc}", file=sys.stderr, flush=True)
            continue
        status = result.get("status", "success") if isinstance(result, dict) else ("success" if result == 0 else "partial")
        if status != "success":
            failures.append((name, str(result.get("error_message", status))[:300] if isinstance(result, dict) else status))
        print(f"[{datetime.now():%H:%M:%S}] {name} {status}", flush=True)

    if failures:
        print("Steps needing attention:", file=sys.stderr)
        for name, message in failures:
            print(f"  {name}: {message}", file=sys.stderr)
        return 1
    print(f"Refresh through {args.end_date} completed.")
    return 0


def run_futures_refresh(args: argparse.Namespace, loop: dict):
    """Refresh contract master, main-contract mapping, and quotes of contracts still trading."""
    single = {key: loop[key] for key in ("dry_run", "max_retries", "retry_interval")}
    results = [
        run_futures_basic_etl(args.token, **single),
        run_futures_mapping_etl(args.token, end_date=args.end_date, **single),
        run_futures_daily_etl(
            args.token,
            load_contract_codes(FUTURES_BASIC_PATH, DEFAULT_INDEX_FUTURES_PRODUCTS, args.end_date),
            end_date=args.end_date,
            **loop,
        ),
    ]
    failed = [r for r in results if r.get("status") != "success"]
    return {"status": "success" if not failed else "partial", "error_message": "; ".join(r.get("error_message", "") for r in failed)}


def run_extended_update(args: argparse.Namespace):
    """Run build_extended_history in update mode and map its exit code to a status."""
    # Reuse the workflow's own argument parsing so defaults stay in one place.
    argv = ["--end-date", args.end_date, "--update", "--request-interval", str(args.request_interval), "--progress-every", str(args.progress_every)]
    if args.dry_run:
        argv.append("--dry-run")
    saved = sys.argv
    sys.argv = ["build_extended_history.py", *argv]
    try:
        code = build_extended_history.main()
    finally:
        sys.argv = saved
    return {"status": "success" if code == 0 else "partial", "error_message": "see build_extended_history output above"}


if __name__ == "__main__":
    raise SystemExit(main())
