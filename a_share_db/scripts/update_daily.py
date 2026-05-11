#!/usr/bin/env python3
"""Incrementally update daily prices, adj factors, and adjusted daily files.

For each selected stock, this script reads the max local trade_date from
data/market_data/daily/none/{code}.csv, fetches missing rows from the next day
through --end-date, merges by trade_date, and rewrites the same CSV file.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.daily import ADJ_FACTOR_COLUMNS, DAILY_PRICE_COLUMNS
from a_share_db.constant.paths import (
    ADJ_FACTOR_ROOT,
    BACKUP_ROOT,
    DAILY_NONE_ROOT,
    DAILY_ROOT,
    ETL_LOG_PATH,
    RAW_TUSHARE_ADJ_FACTOR_ROOT,
    RAW_TUSHARE_DAILY_NONE_ROOT,
    STOCK_BASIC_PATH,
)
from a_share_db.progress import ProgressReporter
from a_share_db.scripts.build_adjusted_daily import (
    ADJUSTED_TYPES,
    build_adjusted_daily,
    write_csv as write_adjusted_csv,
)
from a_share_db.scripts.fetch_adj_factor import (
    convert_tushare_adj_factor,
    fetch_with_retries as fetch_adj_factor_with_retries,
    write_csv as write_adj_factor_csv,
)
from a_share_db.scripts.fetch_daily import (
    convert_tushare_daily,
    fetch_with_retries as fetch_daily_with_retries,
    load_requested_codes,
    read_stock_basic,
    select_stock_rows,
    write_csv as write_daily_csv,
)
from a_share_db.scripts.provider_codes import build_tushare_ts_code


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STOCK_BASIC = STOCK_BASIC_PATH
DEFAULT_DAILY_ROOT = DAILY_NONE_ROOT
DEFAULT_ADJ_FACTOR_ROOT = ADJ_FACTOR_ROOT
DEFAULT_DAILY_OUTPUT_ROOT = DAILY_ROOT
DEFAULT_RAW_DAILY_ROOT = RAW_TUSHARE_DAILY_NONE_ROOT
DEFAULT_RAW_ADJ_FACTOR_ROOT = RAW_TUSHARE_ADJ_FACTOR_ROOT
DEFAULT_LOG = ETL_LOG_PATH
DEFAULT_BACKUP_ROOT = BACKUP_ROOT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Incrementally update local daily none, adj_factor, and qfq/hfq CSV files."
        )
    )
    parser.add_argument(
        "--token",
        default=os.getenv("TUSHARE_TOKEN"),
        help="Tushare token. Defaults to env var TUSHARE_TOKEN.",
    )
    parser.add_argument(
        "--codes",
        nargs="+",
        help="Local 6-digit stock codes to update, for example 600519 000001.",
    )
    parser.add_argument(
        "--codes-file",
        type=Path,
        help="Text file with one local 6-digit stock code per line.",
    )
    parser.add_argument(
        "--all-stocks",
        action="store_true",
        help="Update every listed stock in data/metadata/stock_basic.csv.",
    )
    parser.add_argument(
        "--stock-basic",
        type=Path,
        default=DEFAULT_STOCK_BASIC,
        help=f"Local stock_basic.csv path. Default: {DEFAULT_STOCK_BASIC}",
    )
    parser.add_argument(
        "--start-date",
        help=(
            "Minimum update start date in YYYYMMDD or YYYY-MM-DD format. "
            "Existing files still start from max(local trade_date)+1 when later."
        ),
    )
    parser.add_argument(
        "--end-date",
        default=datetime.now().strftime("%Y%m%d"),
        help="Update end date in YYYYMMDD or YYYY-MM-DD format. Default: today.",
    )
    parser.add_argument(
        "--init-missing",
        action="store_true",
        help=(
            "Initialize stocks whose local none daily file is missing. "
            "Uses --start-date when provided, otherwise stock_basic list_date."
        ),
    )
    parser.add_argument(
        "--daily-root",
        type=Path,
        default=DEFAULT_DAILY_ROOT,
        help=f"Unadjusted daily directory. Default: {DEFAULT_DAILY_ROOT}",
    )
    parser.add_argument(
        "--adj-factor-root",
        type=Path,
        default=DEFAULT_ADJ_FACTOR_ROOT,
        help=f"Adj factor directory. Default: {DEFAULT_ADJ_FACTOR_ROOT}",
    )
    parser.add_argument(
        "--daily-output-root",
        type=Path,
        default=DEFAULT_DAILY_OUTPUT_ROOT,
        help=f"Daily output root for qfq/hfq. Default: {DEFAULT_DAILY_OUTPUT_ROOT}",
    )
    parser.add_argument(
        "--adjust-types",
        nargs="+",
        choices=ADJUSTED_TYPES,
        default=ADJUSTED_TYPES,
        help="Adjusted price types to rebuild after updates. Default: qfq hfq.",
    )
    parser.add_argument(
        "--no-adj-factor",
        action="store_true",
        help="Do not update adj_factor files.",
    )
    parser.add_argument(
        "--no-adjusted",
        action="store_true",
        help="Do not rebuild qfq/hfq files after daily updates.",
    )
    parser.add_argument(
        "--raw-daily-root",
        type=Path,
        default=DEFAULT_RAW_DAILY_ROOT,
        help=f"Raw Tushare daily directory when --with-raw is set. Default: {DEFAULT_RAW_DAILY_ROOT}",
    )
    parser.add_argument(
        "--raw-adj-factor-root",
        type=Path,
        default=DEFAULT_RAW_ADJ_FACTOR_ROOT,
        help=(
            "Raw Tushare adj_factor directory when --with-raw is set. "
            f"Default: {DEFAULT_RAW_ADJ_FACTOR_ROOT}"
        ),
    )
    parser.add_argument(
        "--with-raw",
        action="store_true",
        help="Also merge raw Tushare daily and adj_factor rows.",
    )
    parser.add_argument(
        "--limit-stocks",
        type=int,
        help="Update only the first N selected stocks. Useful for smoke tests.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and merge dataframes, but do not write CSV files or logs.",
    )
    parser.add_argument(
        "--request-interval",
        type=float,
        default=0.13,
        help="Seconds to sleep between Tushare requests. Default: 0.13.",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=50,
        help="Print progress every N stocks. Use 0 to disable progress output. Default: 50.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum attempts per stock request. Default: 3.",
    )
    parser.add_argument(
        "--retry-interval",
        type=float,
        default=5.0,
        help="Seconds to sleep between retries. Default: 5.",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop immediately when one stock fails instead of continuing.",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Do not append execution status to data/logs/etl_log.csv.",
    )
    parser.add_argument(
        "--backup-root",
        type=Path,
        default=DEFAULT_BACKUP_ROOT,
        help=f"Backup directory for existing CSV files. Default: {DEFAULT_BACKUP_ROOT}",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not move existing output files to backups before replacing them.",
    )
    return parser.parse_args()


def import_pandas():
    try:
        import pandas as pd
    except ImportError as exc:
        raise SystemExit("Missing dependency. Install with: python -m pip install pandas") from exc
    return pd


def parse_date_arg(value: str | None) -> date | None:
    if not value:
        return None
    text = str(value).strip()
    if len(text) == 8 and text.isdigit():
        return datetime.strptime(text, "%Y%m%d").date()
    return datetime.strptime(text, "%Y-%m-%d").date()


def provider_date(value: date | None) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y%m%d")


def local_date(value: date | None) -> str:
    if value is None:
        return ""
    return value.strftime("%Y-%m-%d")


def read_existing_csv(path: Path, columns: list[str]):
    pd = import_pandas()
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=columns)
    frame = pd.read_csv(path, dtype={"code": str, "trade_date": str})
    for column in columns:
        if column not in frame.columns:
            frame[column] = ""
    return frame[columns]


def max_trade_date(frame) -> date | None:
    if frame.empty or "trade_date" not in frame.columns:
        return None
    dates = frame["trade_date"].dropna().astype(str)
    dates = dates[dates.str.fullmatch(r"\d{4}-\d{2}-\d{2}")]
    if dates.empty:
        return None
    return datetime.strptime(dates.max(), "%Y-%m-%d").date()


def min_trade_date(frame) -> date | None:
    if frame.empty or "trade_date" not in frame.columns:
        return None
    dates = frame["trade_date"].dropna().astype(str)
    dates = dates[dates.str.fullmatch(r"\d{4}-\d{2}-\d{2}")]
    if dates.empty:
        return None
    return datetime.strptime(dates.min(), "%Y-%m-%d").date()


def parse_stock_list_date(value: str | None) -> date | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return parse_date_arg(text)
    except ValueError:
        return None


def choose_start_date(
    existing_daily,
    requested_start: date | None,
    stock_list_date: date | None,
    init_missing: bool,
) -> tuple[date | None, str | None]:
    last_trade_date = max_trade_date(existing_daily)
    if last_trade_date is not None:
        start = last_trade_date + timedelta(days=1)
        if requested_start is not None and requested_start > start:
            start = requested_start
        return start, local_date(last_trade_date)

    if not init_missing:
        return None, None

    start = requested_start or stock_list_date
    return start, None


def merge_local_rows(existing, new_rows, columns: list[str]):
    pd = import_pandas()
    if existing.empty:
        merged = new_rows.copy()
    elif new_rows.empty:
        merged = existing.copy()
    else:
        merged = pd.concat([existing, new_rows], ignore_index=True)
    for column in columns:
        if column not in merged.columns:
            merged[column] = ""
    if not merged.empty:
        merged["code"] = merged["code"].astype(str).str.zfill(6)
        merged = merged.drop_duplicates(subset=["code", "trade_date"], keep="last")
        merged = merged.sort_values(["code", "trade_date"], kind="stable")
    return merged[columns]


def merge_raw_rows(existing_path: Path, raw_rows, subset: list[str]):
    pd = import_pandas()
    if raw_rows.empty:
        if existing_path.exists() and existing_path.stat().st_size > 0:
            return pd.read_csv(existing_path, dtype=str).fillna("")
        return raw_rows.copy()

    if existing_path.exists() and existing_path.stat().st_size > 0:
        existing = pd.read_csv(existing_path, dtype=str).fillna("")
        merged = pd.concat([existing, raw_rows], ignore_index=True)
    else:
        merged = raw_rows.copy()

    for column in subset:
        if column not in merged.columns:
            merged[column] = ""
    merged = merged.drop_duplicates(subset=subset, keep="last")
    sort_columns = [column for column in subset if column in merged.columns]
    if sort_columns:
        merged = merged.sort_values(sort_columns, kind="stable")
    return merged


def append_etl_log(
    log_path: Path,
    start_time: str,
    end_time: str,
    status: str,
    row_count: int,
    error_message: str,
) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    exists = log_path.exists()
    with log_path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "job_name",
                "source",
                "start_time",
                "end_time",
                "status",
                "row_count",
                "error_message",
            ],
        )
        if not exists:
            writer.writeheader()
        writer.writerow(
            {
                "job_name": "update_daily",
                "source": "tushare/local",
                "start_time": start_time,
                "end_time": end_time,
                "status": status,
                "row_count": row_count,
                "error_message": error_message,
            }
        )


def run_update_daily(
    token: str,
    codes: Iterable[str] | None = None,
    codes_file: Path | None = None,
    all_stocks: bool = False,
    stock_basic_path: Path = DEFAULT_STOCK_BASIC,
    start_date: str | None = None,
    end_date: str | None = None,
    init_missing: bool = False,
    daily_root: Path = DEFAULT_DAILY_ROOT,
    adj_factor_root: Path = DEFAULT_ADJ_FACTOR_ROOT,
    daily_output_root: Path = DEFAULT_DAILY_OUTPUT_ROOT,
    adjust_types: Iterable[str] = ADJUSTED_TYPES,
    update_adj_factor: bool = True,
    rebuild_adjusted: bool = True,
    raw_daily_root: Path = DEFAULT_RAW_DAILY_ROOT,
    raw_adj_factor_root: Path = DEFAULT_RAW_ADJ_FACTOR_ROOT,
    write_raw: bool = False,
    limit_stocks: int | None = None,
    dry_run: bool = False,
    request_interval: float = 0.13,
    progress_every: int = 0,
    max_retries: int = 3,
    retry_interval: float = 5.0,
    stop_on_error: bool = False,
    write_log: bool = True,
    log_path: Path = DEFAULT_LOG,
    backup_root: Path = DEFAULT_BACKUP_ROOT,
    create_backup: bool = True,
) -> dict:
    if not token:
        raise ValueError("Tushare token is required.")

    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    requested_start = parse_date_arg(start_date)
    requested_end = parse_date_arg(end_date) or datetime.now().date()
    if requested_start is not None and requested_start > requested_end:
        raise ValueError("start-date must be less than or equal to end-date.")
    if request_interval < 0:
        raise ValueError("request-interval must be greater than or equal to 0.")
    if retry_interval < 0:
        raise ValueError("retry-interval must be greater than or equal to 0.")

    row_count = 0
    daily_new_rows = 0
    adj_factor_new_rows = 0
    adjusted_rows = 0
    stock_count = 0
    skipped_count = 0
    missing_count = 0
    updated_codes: list[str] = []
    backup_paths: list[str] = []
    failures: list[dict[str, str]] = []
    status = "failed"
    error_message = ""
    backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    try:
        stock_basic = read_stock_basic(Path(stock_basic_path))
        selected_codes = load_requested_codes(codes, codes_file)
        stocks = select_stock_rows(stock_basic, selected_codes, all_stocks, limit_stocks)
        stock_count = len(stocks)
        name_by_code = dict(zip(stock_basic["code"], stock_basic["name"]))
        progress = ProgressReporter(stock_count, every=progress_every, label="Update daily")

        for index, stock in enumerate(stocks.to_dict("records"), start=1):
            code = stock["code"]
            ts_code = build_tushare_ts_code(code, stock.get("exchange", ""))
            daily_path = Path(daily_root) / f"{code}.csv"
            adj_path = Path(adj_factor_root) / f"{code}.csv"

            try:
                existing_daily = read_existing_csv(daily_path, DAILY_PRICE_COLUMNS)
                daily_start, _last_trade_date = choose_start_date(
                    existing_daily,
                    requested_start,
                    parse_stock_list_date(stock.get("list_date")),
                    init_missing,
                )
                if daily_start is None:
                    missing_count += 1
                    skipped_count += 1
                    continue
                merged_daily = existing_daily
                daily_changed = False

                if daily_start <= requested_end:
                    raw_daily = fetch_daily_with_retries(
                        token,
                        ts_code,
                        provider_date(daily_start),
                        provider_date(requested_end),
                        max_retries=max_retries,
                        retry_interval=retry_interval,
                    )
                    if request_interval and update_adj_factor:
                        time.sleep(request_interval)
                    new_daily = convert_tushare_daily(raw_daily, name_by_code)
                    merged_daily = merge_local_rows(existing_daily, new_daily, DAILY_PRICE_COLUMNS)
                    daily_changed = len(merged_daily) > len(existing_daily)
                    daily_new_rows += max(len(merged_daily) - len(existing_daily), 0)
                    row_count += len(new_daily)

                    if not dry_run and daily_changed:
                        backup_path = write_daily_csv(
                            merged_daily,
                            daily_path,
                            backup_root=Path(backup_root),
                            backup_timestamp=backup_timestamp,
                            create_backup=create_backup,
                        )
                        if backup_path:
                            backup_paths.append(str(backup_path))

                    if write_raw and not dry_run and not raw_daily.empty:
                        raw_path = Path(raw_daily_root) / f"{code}.csv"
                        merged_raw = merge_raw_rows(raw_path, raw_daily, ["ts_code", "trade_date"])
                        backup_path = write_daily_csv(
                            merged_raw,
                            raw_path,
                            backup_root=Path(backup_root),
                            backup_timestamp=backup_timestamp,
                            create_backup=create_backup,
                        )
                        if backup_path:
                            backup_paths.append(str(backup_path))

                adj_changed = False
                merged_adj = None
                if update_adj_factor:
                    existing_adj = read_existing_csv(adj_path, ADJ_FACTOR_COLUMNS)
                    adj_last_date = max_trade_date(existing_adj)
                    if adj_last_date is not None:
                        adj_start = adj_last_date + timedelta(days=1)
                        if requested_start is not None and requested_start > adj_start:
                            adj_start = requested_start
                    else:
                        adj_start = requested_start or min_trade_date(merged_daily)

                    merged_adj = existing_adj
                    if adj_start is not None and adj_start <= requested_end:
                        raw_adj = fetch_adj_factor_with_retries(
                            token,
                            ts_code,
                            provider_date(adj_start),
                            provider_date(requested_end),
                            max_retries=max_retries,
                            retry_interval=retry_interval,
                        )
                        new_adj = convert_tushare_adj_factor(raw_adj)
                        merged_adj = merge_local_rows(existing_adj, new_adj, ADJ_FACTOR_COLUMNS)
                        adj_changed = len(merged_adj) > len(existing_adj)
                        adj_factor_new_rows += max(len(merged_adj) - len(existing_adj), 0)
                        row_count += len(new_adj)

                        if not dry_run and adj_changed:
                            backup_path = write_adj_factor_csv(
                                merged_adj,
                                adj_path,
                                backup_root=Path(backup_root),
                                backup_timestamp=backup_timestamp,
                                create_backup=create_backup,
                            )
                            if backup_path:
                                backup_paths.append(str(backup_path))

                        if write_raw and not dry_run and not raw_adj.empty:
                            raw_path = Path(raw_adj_factor_root) / f"{code}.csv"
                            merged_raw = merge_raw_rows(raw_path, raw_adj, ["ts_code", "trade_date"])
                            backup_path = write_adj_factor_csv(
                                merged_raw,
                                raw_path,
                                backup_root=Path(backup_root),
                                backup_timestamp=backup_timestamp,
                                create_backup=create_backup,
                            )
                            if backup_path:
                                backup_paths.append(str(backup_path))

                if rebuild_adjusted and (daily_changed or adj_changed):
                    if merged_adj is None:
                        merged_adj = read_existing_csv(adj_path, ADJ_FACTOR_COLUMNS)
                    for adjust_type in adjust_types:
                        adjusted = build_adjusted_daily(merged_daily, merged_adj, adjust_type)
                        adjusted_rows += len(adjusted)
                        if dry_run:
                            continue
                        output_path = Path(daily_output_root) / adjust_type / f"{code}.csv"
                        backup_path = write_adjusted_csv(
                            adjusted,
                            output_path,
                            backup_root=Path(backup_root),
                            backup_timestamp=backup_timestamp,
                            create_backup=create_backup,
                        )
                        if backup_path:
                            backup_paths.append(str(backup_path))

                if daily_changed or adj_changed:
                    updated_codes.append(code)
                else:
                    skipped_count += 1

                if request_interval:
                    time.sleep(request_interval)
            except Exception as exc:
                failures.append({"code": code, "ts_code": ts_code, "error": str(exc)})
                if stop_on_error:
                    raise
                continue
            finally:
                progress.maybe_print(
                    index,
                    row_count=row_count,
                    skipped_count=skipped_count,
                    failure_count=len(failures),
                    extra=(
                        f"updated={len(updated_codes)} "
                        f"daily_new={daily_new_rows} adj_new={adj_factor_new_rows}"
                    ),
                )

        status = "partial" if failures else "success"
        if failures:
            error_message = "; ".join(
                f"{item['code']}({item['ts_code']}): {item['error']}" for item in failures[:20]
            )
            if len(failures) > 20:
                error_message += f"; ... {len(failures) - 20} more"

        return {
            "status": status,
            "stock_count": stock_count,
            "updated_count": len(updated_codes),
            "updated_codes": updated_codes,
            "skipped_count": skipped_count,
            "missing_count": missing_count,
            "failure_count": len(failures),
            "failures": failures,
            "row_count": row_count,
            "daily_new_rows": daily_new_rows,
            "adj_factor_new_rows": adj_factor_new_rows,
            "adjusted_rows": adjusted_rows,
            "start_date": provider_date(requested_start),
            "end_date": provider_date(requested_end),
            "dry_run": dry_run,
            "backup_paths": backup_paths,
            "error_message": error_message,
        }
    except Exception as exc:
        error_message = str(exc)
        raise
    finally:
        if write_log and not dry_run:
            end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            append_etl_log(
                Path(log_path),
                start_time=start_time,
                end_time=end_time,
                status=status,
                row_count=row_count,
                error_message=error_message,
            )


def main() -> int:
    args = parse_args()
    if not args.token:
        print("Tushare token is required. Set TUSHARE_TOKEN or pass --token.", file=sys.stderr)
        return 2

    try:
        result = run_update_daily(
            token=args.token,
            codes=args.codes,
            codes_file=args.codes_file,
            all_stocks=args.all_stocks,
            stock_basic_path=args.stock_basic,
            start_date=args.start_date,
            end_date=args.end_date,
            init_missing=args.init_missing,
            daily_root=args.daily_root,
            adj_factor_root=args.adj_factor_root,
            daily_output_root=args.daily_output_root,
            adjust_types=args.adjust_types,
            update_adj_factor=not args.no_adj_factor,
            rebuild_adjusted=not args.no_adjusted,
            raw_daily_root=args.raw_daily_root,
            raw_adj_factor_root=args.raw_adj_factor_root,
            write_raw=args.with_raw,
            limit_stocks=args.limit_stocks,
            dry_run=args.dry_run,
            request_interval=args.request_interval,
            progress_every=args.progress_every,
            max_retries=args.max_retries,
            retry_interval=args.retry_interval,
            stop_on_error=args.stop_on_error,
            write_log=not args.no_log,
            backup_root=args.backup_root,
            create_backup=not args.no_backup,
        )
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
            f"adjusted_rebuilt_rows={result['adjusted_rows']}."
        )
        for backup_path in result["backup_paths"]:
            print(f"Backed up previous file to {backup_path}")
        if result["failures"]:
            print("Failures:", file=sys.stderr)
            for item in result["failures"][:20]:
                print(f"  {item['code']} ({item['ts_code']}): {item['error']}", file=sys.stderr)
            if len(result["failures"]) > 20:
                print(f"  ... {len(result['failures']) - 20} more", file=sys.stderr)
            return 1
        return 0
    except Exception as exc:
        print(f"update_daily failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
