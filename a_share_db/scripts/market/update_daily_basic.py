#!/usr/bin/env python3
"""Incrementally update daily basic indicators.

For each selected stock, read the max local trade_date from
data/market_data/daily_basic/{code}.csv, fetch missing rows from the next day
through --end-date, merge by code + trade_date, and rewrite the same file.
Stocks without a local file are initialized from their list date.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import timedelta
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.commands import DEFAULT_HISTORY_START_DATE
from a_share_db.constant.daily_basic import DAILY_BASIC_COLUMNS
from a_share_db.constant.paths import DAILY_BASIC_ROOT
from a_share_db.scripts.market.fetch_daily_basic import convert_tushare_daily_basic, fetch_with_retries
from a_share_db.utils.cli import (
    add_date_range_arguments,
    add_run_control_arguments,
    add_stock_selection_arguments,
    add_token_argument,
    require_token,
    run_control_kwargs,
    run_main,
    stock_selection_kwargs,
)
from a_share_db.utils.etl_common import (
    load_requested_codes,
    merge_rows,
    parse_date_arg,
    provider_date,
    read_existing_csv,
    read_stock_basic,
    select_stock_rows,
)
from a_share_db.utils.etl_runners import EtlRun
from a_share_db.utils.progress import ProgressReporter
from a_share_db.utils.provider_codes import build_tushare_ts_code


DEFAULT_OUTPUT_ROOT = DAILY_BASIC_ROOT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Incrementally update data/market_data/daily_basic/{code}.csv.")
    add_token_argument(parser)
    add_stock_selection_arguments(parser)
    add_date_range_arguments(parser, default_start=None, end_defaults_to_today=True)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT, help=f"daily_basic directory. Default: {DEFAULT_OUTPUT_ROOT}")
    add_run_control_arguments(parser, resumable=False)
    return parser.parse_args()


def max_local_date(frame):
    if frame.empty:
        return None
    dates = frame["trade_date"].dropna().astype(str)
    dates = dates[dates.str.fullmatch(r"\d{4}-\d{2}-\d{2}")]
    return parse_date_arg(dates.max()) if not dates.empty else None


def run_update_daily_basic(
    token: str,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    start_date: str | None = None,
    end_date: str | None = None,
    codes=None,
    codes_file=None,
    all_stocks: bool = False,
    stock_basic_path=None,
    statuses=("listed",),
    limit_stocks: int | None = None,
    dry_run: bool = False,
    write_log: bool = True,
    log_path=None,
    backup_root=None,
    create_backup: bool = False,
    request_interval: float = 0.13,
    progress_every: int = 0,
    max_retries: int = 3,
    retry_interval: float = 5.0,
    stop_on_error: bool = False,
) -> dict:
    from a_share_db.constant.paths import BACKUP_ROOT, ETL_LOG_PATH, STOCK_BASIC_PATH

    if not token:
        raise ValueError("Tushare token is required.")
    run = EtlRun("update_daily_basic", log_path or ETL_LOG_PATH, write_log, dry_run, backup_root or BACKUP_ROOT)
    requested_start = parse_date_arg(start_date)
    requested_end = parse_date_arg(end_date)
    stock_count = 0
    new_rows = 0
    try:
        stock_basic = read_stock_basic(Path(stock_basic_path or STOCK_BASIC_PATH), statuses)
        stocks = select_stock_rows(stock_basic, load_requested_codes(codes, codes_file), all_stocks, limit_stocks)
        stock_count = len(stocks)
        progress = ProgressReporter(stock_count, every=progress_every, label="Update daily_basic")
        for index, stock in enumerate(stocks.to_dict("records"), start=1):
            code = stock["code"]
            path = Path(output_root) / f"{code}.csv"
            ts_code = ""
            try:
                existing = read_existing_csv(path, DAILY_BASIC_COLUMNS)
                last_date = max_local_date(existing)
                if last_date is not None:
                    # The local file is the checkpoint: continue from the day after it ends.
                    start = last_date + timedelta(days=1)
                    if requested_start and requested_start > start:
                        start = requested_start
                else:
                    start = requested_start or parse_date_arg(stock.get("list_date") or None) or parse_date_arg(DEFAULT_HISTORY_START_DATE)
                if requested_end and start > requested_end:
                    run.skipped_count += 1
                    continue
                ts_code = build_tushare_ts_code(code, stock.get("exchange", ""))
                raw = fetch_with_retries(token, ts_code, provider_date(start), provider_date(requested_end), max_retries, retry_interval)
                fresh = convert_tushare_daily_basic(raw)
                if fresh.empty:
                    run.skipped_count += 1
                else:
                    merged = merge_rows(existing, fresh, DAILY_BASIC_COLUMNS, ["code", "trade_date"])
                    added = max(len(merged) - len(existing), 0)
                    new_rows += added
                    run.row_count += len(fresh)
                    if added:
                        run.write(merged, path, create_backup)
                if request_interval:
                    time.sleep(request_interval)
            except Exception as exc:
                run.failures.append({"item": f"{code}({ts_code})", "code": code, "error": str(exc)})
                if stop_on_error:
                    raise
            finally:
                progress.maybe_print(index, row_count=run.row_count, skipped_count=run.skipped_count, failure_count=len(run.failures), extra=f"new={new_rows}")
        run.finish()
        return run.result(stock_count=stock_count, new_rows=new_rows, output_root=str(output_root))
    except Exception as exc:
        run.fail(exc)
        raise
    finally:
        run.log()


def main() -> int:
    args = parse_args()
    if not require_token(args):
        return 2
    return run_main(
        "update_daily_basic",
        lambda: run_update_daily_basic(
            token=args.token,
            output_root=args.output_root,
            start_date=args.start_date,
            end_date=args.end_date,
            **stock_selection_kwargs(args),
            **run_control_kwargs(args),
        ),
        unit="stocks",
    )


if __name__ == "__main__":
    raise SystemExit(main())
