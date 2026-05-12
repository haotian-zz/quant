#!/usr/bin/env python3
"""Fetch unadjusted A-share historical minute bars from Tushare.

Outputs:
data/market_data/minute/{frequency}/none/{code}.csv
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.minute import (
    DEFAULT_MINUTE_WINDOW_TRADING_DAYS,
    MINUTE_BAR_COLUMNS,
    MINUTE_FREQUENCIES,
    TUSHARE_MINUTE_FIELDS,
    TUSHARE_MINUTE_FREQ_MAP,
    TUSHARE_MINUTE_FREQ_REVERSE_MAP,
)
from a_share_db.constant.paths import (
    BACKUP_ROOT,
    ETL_LOG_PATH,
    MINUTE_ROOT,
    RAW_TUSHARE_MINUTE_ROOT,
    STOCK_BASIC_PATH,
    TRADE_CALENDAR_PATH,
)
from a_share_db.scripts.market.fetch_daily import (
    build_backup_timestamp,
    import_pandas,
    import_tushare,
    load_requested_codes,
    read_stock_basic,
    select_stock_rows,
    write_csv,
)
from a_share_db.utils.progress import ProgressReporter
from a_share_db.utils.provider_codes import build_tushare_ts_code


# Defaults mirror the other market ETL scripts so commands stay predictable.
DEFAULT_STOCK_BASIC = STOCK_BASIC_PATH
DEFAULT_OUTPUT_ROOT = MINUTE_ROOT
DEFAULT_RAW_OUTPUT_ROOT = RAW_TUSHARE_MINUTE_ROOT
DEFAULT_LOG = ETL_LOG_PATH
DEFAULT_BACKUP_ROOT = BACKUP_ROOT
DEFAULT_TRADE_CALENDAR = TRADE_CALENDAR_PATH

# This is only a fallback when local trade_calendar.csv is not available.
DEFAULT_WINDOW_DAYS = 20


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch Tushare stk_mins data and build "
            "data/market_data/minute/{frequency}/none/{code}.csv."
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
        help="Local 6-digit stock codes to fetch, for example 600519 000001.",
    )
    parser.add_argument(
        "--codes-file",
        type=Path,
        help="Text file with one local 6-digit stock code per line.",
    )
    parser.add_argument(
        "--all-stocks",
        action="store_true",
        help="Fetch every listed stock in data/metadata/stock_basic.csv.",
    )
    parser.add_argument(
        "--stock-basic",
        type=Path,
        default=DEFAULT_STOCK_BASIC,
        help=f"Local stock_basic.csv path. Default: {DEFAULT_STOCK_BASIC}",
    )
    parser.add_argument(
        "--frequencies",
        nargs="+",
        default=["1m"],
        help="Minute frequencies to fetch. Supports 1m/5m/15m/30m/60m and Tushare 1min style. Default: 1m.",
    )
    parser.add_argument(
        "--start-date",
        help=(
            "Start datetime. Supports YYYYMMDD, YYYY-MM-DD, or "
            "'YYYY-MM-DD HH:MM:SS'. Date-only values start at 00:00:00."
        ),
    )
    parser.add_argument(
        "--end-date",
        help=(
            "End datetime. Supports YYYYMMDD, YYYY-MM-DD, or "
            "'YYYY-MM-DD HH:MM:SS'. Date-only values end at 23:59:59."
        ),
    )
    parser.add_argument(
        "--trade-calendar",
        type=Path,
        default=DEFAULT_TRADE_CALENDAR,
        help=f"Local trade_calendar.csv path for trading-day windows. Default: {DEFAULT_TRADE_CALENDAR}",
    )
    parser.add_argument(
        "--window-trading-days",
        type=int,
        help=(
            "Override trading days per request for every frequency. "
            "By default each frequency uses the largest safe value below 8000 rows."
        ),
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=DEFAULT_WINDOW_DAYS,
        help=(
            "Fallback calendar days per request when trade_calendar.csv is missing. "
            f"Default: {DEFAULT_WINDOW_DAYS}."
        ),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help=f"Output root directory. Default: {DEFAULT_OUTPUT_ROOT}",
    )
    parser.add_argument(
        "--raw-output-root",
        type=Path,
        default=DEFAULT_RAW_OUTPUT_ROOT,
        help=f"Raw output root when --with-raw is set. Default: {DEFAULT_RAW_OUTPUT_ROOT}",
    )
    parser.add_argument(
        "--with-raw",
        action="store_true",
        help="Also write raw Tushare minute CSV files.",
    )
    parser.add_argument(
        "--limit-stocks",
        type=int,
        help="Fetch only the first N selected stocks. Useful for smoke tests.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and convert data, but do not write CSV files or logs.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip stock/frequency files that already exist and are non-empty.",
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
        help="Print progress every N stock/frequency jobs. Use 0 to disable progress output. Default: 50.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum attempts per request window before recording a failure. Default: 3.",
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
        help="Stop immediately when one stock/frequency fails instead of continuing.",
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
        "--backup",
        dest="create_backup",
        action="store_true",
        help="Move existing output files to backups before replacing them. Default: off.",
    )
    parser.add_argument("--no-backup", dest="create_backup", action="store_false", help=argparse.SUPPRESS)
    parser.set_defaults(create_backup=False)
    return parser.parse_args()


def normalize_frequency(value: str) -> str:
    text = str(value).strip().lower()
    if not text:
        raise ValueError("frequency cannot be empty.")
    # Accept both local names such as 1m and Tushare names such as 1min.
    if text in TUSHARE_MINUTE_FREQ_REVERSE_MAP:
        return TUSHARE_MINUTE_FREQ_REVERSE_MAP[text]
    if text in MINUTE_FREQUENCIES:
        return text
    raise ValueError(f"Unsupported minute frequency: {value}")


def normalize_frequencies(values: Iterable[str]) -> list[str]:
    normalized = []
    seen = set()
    for value in values:
        frequency = normalize_frequency(value)
        if frequency not in seen:
            # Keep caller order but avoid fetching the same frequency twice.
            normalized.append(frequency)
            seen.add(frequency)
    return normalized


def parse_datetime_arg(value: str | None, end_of_day: bool = False) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if len(text) == 8 and text.isdigit():
        # Date-only CLI values expand to a full-day window.
        parsed = datetime.strptime(text, "%Y%m%d")
        return parsed.replace(hour=23, minute=59, second=59) if end_of_day else parsed
    if len(text) == 10:
        parsed = datetime.strptime(text, "%Y-%m-%d")
        return parsed.replace(hour=23, minute=59, second=59) if end_of_day else parsed
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y%m%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unsupported datetime format: {value}")


def provider_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    # stk_mins expects a datetime string, not the YYYYMMDD date used by daily.
    return value.strftime("%Y-%m-%d %H:%M:%S")


def build_calendar_day_windows(
    start_dt: datetime | None,
    end_dt: datetime | None,
    window_days: int,
) -> list[tuple[datetime | None, datetime | None]]:
    if start_dt is None or end_dt is None:
        # Let Tushare apply its default range when either bound is missing.
        return [(start_dt, end_dt)]
    if start_dt > end_dt:
        raise ValueError("start-date must be less than or equal to end-date.")
    if window_days < 1:
        raise ValueError("window-days must be greater than or equal to 1.")

    windows = []
    current = start_dt
    step = timedelta(days=window_days)
    while current <= end_dt:
        # Windows are inclusive and non-overlapping at one-second precision.
        window_end = min(current + step - timedelta(seconds=1), end_dt)
        windows.append((current, window_end))
        current = window_end + timedelta(seconds=1)
    return windows


def read_trade_dates(path: Path, start_dt: datetime | None, end_dt: datetime | None) -> list:
    pd = import_pandas()
    if not path.exists() or start_dt is None or end_dt is None:
        return []
    frame = pd.read_csv(path, dtype=str).fillna("")
    required = {"calendar_date", "is_trading_day"}
    if not required.issubset(frame.columns):
        return []

    trading = frame[frame["is_trading_day"].astype(str).isin({"1", "1.0", "true", "True"})].copy()
    dates = pd.to_datetime(trading["calendar_date"], errors="coerce").dropna()
    if dates.empty:
        return []
    start_date = start_dt.date()
    end_date = end_dt.date()
    unique_dates = sorted({item.date() for item in dates if start_date <= item.date() <= end_date})
    return unique_dates


def window_trading_days_for_frequency(frequency: str, override: int | None = None) -> int:
    if override is not None:
        if override < 1:
            raise ValueError("window-trading-days must be greater than or equal to 1.")
        return override
    return DEFAULT_MINUTE_WINDOW_TRADING_DAYS[frequency]


def build_trading_day_windows(
    start_dt: datetime,
    end_dt: datetime,
    trade_dates: list,
    window_trading_days: int,
) -> list[tuple[datetime, datetime]]:
    if start_dt > end_dt:
        raise ValueError("start-date must be less than or equal to end-date.")
    if window_trading_days < 1:
        raise ValueError("window-trading-days must be greater than or equal to 1.")
    if not trade_dates:
        return []

    windows = []
    for start_index in range(0, len(trade_dates), window_trading_days):
        chunk = trade_dates[start_index : start_index + window_trading_days]
        chunk_start_date = chunk[0]
        chunk_end_date = chunk[-1]
        window_start = datetime.combine(chunk_start_date, datetime.min.time())
        window_end = datetime.combine(chunk_end_date, datetime.max.time().replace(microsecond=0))
        if chunk_start_date == start_dt.date():
            window_start = start_dt
        if chunk_end_date == end_dt.date():
            window_end = end_dt
        windows.append((window_start, window_end))
    return windows


def build_request_windows(
    frequency: str,
    start_dt: datetime | None,
    end_dt: datetime | None,
    trade_dates: list,
    window_trading_days: int,
    fallback_window_days: int,
) -> list[tuple[datetime | None, datetime | None]]:
    if start_dt is None or end_dt is None:
        return [(start_dt, end_dt)]
    if trade_dates:
        # Prefer trading-day windows so each request uses as much of the 8000-row
        # limit as possible without crossing it.
        windows = build_trading_day_windows(start_dt, end_dt, trade_dates, window_trading_days)
        if windows:
            return windows
    # Fallback keeps the command usable before trade_calendar.csv is built.
    return build_calendar_day_windows(start_dt, end_dt, fallback_window_days)


def fetch_from_tushare(
    token: str,
    ts_code: str,
    provider_freq: str,
    start_dt: datetime | None,
    end_dt: datetime | None,
):
    # Provider identifiers are created at request time and never stored in the
    # formal minute table.
    ts = import_tushare()
    ts.set_token(token)
    pro = ts.pro_api()
    frame = pro.stk_mins(
        ts_code=ts_code,
        freq=provider_freq,
        start_date=provider_datetime(start_dt),
        end_date=provider_datetime(end_dt),
        fields=",".join(TUSHARE_MINUTE_FIELDS),
    )
    pd = import_pandas()
    if frame is None:
        frame = pd.DataFrame(columns=TUSHARE_MINUTE_FIELDS)
    # Keep conversion stable even if the provider omits a column.
    for column in TUSHARE_MINUTE_FIELDS:
        if column not in frame.columns:
            frame[column] = ""
    return frame[TUSHARE_MINUTE_FIELDS]


def fetch_with_retries(
    token: str,
    ts_code: str,
    provider_freq: str,
    start_dt: datetime | None,
    end_dt: datetime | None,
    max_retries: int,
    retry_interval: float,
):
    if max_retries < 1:
        raise ValueError("max-retries must be greater than or equal to 1.")
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            return fetch_from_tushare(token, ts_code, provider_freq, start_dt, end_dt)
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                # Retry transient provider or network failures before marking the job failed.
                time.sleep(retry_interval)
    raise last_error


def fetch_windows(
    token: str,
    ts_code: str,
    provider_freq: str,
    windows: list[tuple[datetime | None, datetime | None]],
    request_interval: float,
    max_retries: int,
    retry_interval: float,
):
    pd = import_pandas()
    frames = []
    for index, (window_start, window_end) in enumerate(windows, start=1):
        # Each window is a separate provider call because stk_mins has a row cap.
        frame = fetch_with_retries(
            token,
            ts_code,
            provider_freq,
            window_start,
            window_end,
            max_retries=max_retries,
            retry_interval=retry_interval,
        )
        if frame is not None and not frame.empty:
            frames.append(frame)
        if request_interval and index < len(windows):
            time.sleep(request_interval)
    if not frames:
        return pd.DataFrame(columns=TUSHARE_MINUTE_FIELDS)
    raw = pd.concat(frames, ignore_index=True)
    # Overlapping reruns or provider duplicates should keep only one bar.
    raw = raw.drop_duplicates(subset=["ts_code", "trade_time"], keep="last")
    raw = raw.sort_values(["ts_code", "trade_time"], kind="stable")
    return raw[TUSHARE_MINUTE_FIELDS]


def convert_tushare_minute(raw, name_by_code: dict[str, str], frequency: str):
    """Convert raw Tushare stk_mins rows into the local minute-bar schema."""
    pd = import_pandas()
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    output = pd.DataFrame()

    output["code"] = raw["ts_code"].fillna("").astype(str).str.split(".").str[0].str.zfill(6)
    output["name"] = output["code"].map(name_by_code).fillna("")
    parsed_time = pd.to_datetime(raw["trade_time"], errors="coerce")
    # trade_time is treated as the bar end timestamp in the local schema.
    output["trade_date"] = parsed_time.dt.strftime("%Y-%m-%d").fillna("")
    output["bar_end_time"] = parsed_time.dt.strftime("%Y-%m-%d %H:%M:%S").fillna("")
    output["frequency"] = frequency
    output["open"] = raw["open"]
    output["high"] = raw["high"]
    output["low"] = raw["low"]
    output["close"] = raw["close"]
    # Tushare stk_mins already returns volume in shares and amount in yuan.
    output["volume"] = raw["vol"]
    output["amount"] = raw["amount"]
    output["adjust_type"] = "none"
    output["update_time"] = update_time

    output = output[MINUTE_BAR_COLUMNS]
    output = output[output["code"].str.fullmatch(r"\d{6}", na=False)]
    output = output[output["bar_end_time"].str.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", na=False)]
    # The local key is code + frequency + adjust_type + bar_end_time.
    output = output.drop_duplicates(subset=["code", "frequency", "adjust_type", "bar_end_time"], keep="last")
    output = output.sort_values(["code", "bar_end_time"], kind="stable")
    return output


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
                "job_name": "fetch_minute",
                "source": "tushare",
                "start_time": start_time,
                "end_time": end_time,
                "status": status,
                "row_count": row_count,
                "error_message": error_message,
            }
        )


def run_minute_etl(
    token: str,
    codes: Iterable[str] | None = None,
    codes_file: Path | None = None,
    all_stocks: bool = False,
    stock_basic_path: Path = DEFAULT_STOCK_BASIC,
    frequencies: Iterable[str] = ("1m",),
    start_date: str | None = None,
    end_date: str | None = None,
    trade_calendar_path: Path = DEFAULT_TRADE_CALENDAR,
    window_trading_days: int | None = None,
    window_days: int = DEFAULT_WINDOW_DAYS,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    raw_output_root: Path = DEFAULT_RAW_OUTPUT_ROOT,
    write_raw: bool = False,
    limit_stocks: int | None = None,
    dry_run: bool = False,
    write_log: bool = True,
    log_path: Path = DEFAULT_LOG,
    backup_root: Path = DEFAULT_BACKUP_ROOT,
    create_backup: bool = False,
    resume: bool = False,
    request_interval: float = 0.13,
    progress_every: int = 0,
    max_retries: int = 3,
    retry_interval: float = 5.0,
    stop_on_error: bool = False,
) -> dict:
    if not token:
        raise ValueError("Tushare token is required.")

    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row_count = 0
    request_count = 0
    status = "failed"
    error_message = ""
    backup_timestamp = build_backup_timestamp()
    backup_paths = []
    stock_count = 0
    job_count = 0
    skipped_count = 0
    failures = []

    try:
        if request_interval < 0:
            raise ValueError("request-interval must be greater than or equal to 0.")
        if retry_interval < 0:
            raise ValueError("retry-interval must be greater than or equal to 0.")

        local_frequencies = normalize_frequencies(frequencies)
        start_dt = parse_datetime_arg(start_date, end_of_day=False)
        end_dt = parse_datetime_arg(end_date, end_of_day=True)
        trade_dates = read_trade_dates(Path(trade_calendar_path), start_dt, end_dt)
        windows_by_frequency = {}
        trading_days_by_frequency = {}
        for frequency in local_frequencies:
            trading_days = window_trading_days_for_frequency(frequency, window_trading_days)
            trading_days_by_frequency[frequency] = trading_days
            windows_by_frequency[frequency] = build_request_windows(
                frequency,
                start_dt,
                end_dt,
                trade_dates,
                trading_days,
                window_days,
            )

        stock_basic = read_stock_basic(Path(stock_basic_path))
        selected_codes = load_requested_codes(codes, codes_file)
        stocks = select_stock_rows(stock_basic, selected_codes, all_stocks, limit_stocks)
        stock_count = len(stocks)
        job_count = stock_count * len(local_frequencies)
        name_by_code = dict(zip(stock_basic["code"], stock_basic["name"]))
        # Progress counts stock/frequency jobs, while request_count tracks
        # underlying Tushare windows.
        progress = ProgressReporter(job_count, every=progress_every, label="Fetch minute")

        current_job = 0
        for stock in stocks.to_dict("records"):
            code = stock["code"]
            ts_code = build_tushare_ts_code(code, stock.get("exchange", ""))
            for frequency in local_frequencies:
                current_job += 1
                output_path = Path(output_root) / frequency / "none" / f"{code}.csv"
                provider_freq = TUSHARE_MINUTE_FREQ_MAP[frequency]
                windows = windows_by_frequency[frequency]
                try:
                    if resume and output_path.exists() and output_path.stat().st_size > 0:
                        # Full-history fetch can skip completed stock/frequency files.
                        skipped_count += 1
                        progress.maybe_print(
                            current_job,
                            row_count=row_count,
                            skipped_count=skipped_count,
                            failure_count=len(failures),
                            extra=(
                                f"requests={request_count} "
                                f"window_trading_days={trading_days_by_frequency[frequency]}"
                            ),
                        )
                        continue

                    raw = fetch_windows(
                        token,
                        ts_code,
                        provider_freq,
                        windows,
                        request_interval=request_interval,
                        max_retries=max_retries,
                        retry_interval=retry_interval,
                    )
                    request_count += len(windows)
                    normalized = convert_tushare_minute(raw, name_by_code, frequency)
                    row_count += len(normalized)

                    if not dry_run:
                        # write_csv uses a temp file and optional backup.
                        backup_path = write_csv(
                            normalized,
                            output_path,
                            backup_root=Path(backup_root),
                            backup_timestamp=backup_timestamp,
                            create_backup=create_backup,
                        )
                        if backup_path:
                            backup_paths.append(str(backup_path))

                    if write_raw and not dry_run:
                        # Raw output keeps provider fields for debugging only.
                        backup_path = write_csv(
                            raw,
                            Path(raw_output_root) / frequency / f"{code}.csv",
                            backup_root=Path(backup_root),
                            backup_timestamp=backup_timestamp,
                            create_backup=create_backup,
                        )
                        if backup_path:
                            backup_paths.append(str(backup_path))

                    if request_interval:
                        time.sleep(request_interval)
                except Exception as exc:
                    # Keep long all-stock jobs running unless stop-on-error is requested.
                    failures.append(
                        {
                            "code": code,
                            "ts_code": ts_code,
                            "frequency": frequency,
                            "error": str(exc),
                        }
                    )
                    if stop_on_error:
                        raise
                finally:
                    progress.maybe_print(
                        current_job,
                        row_count=row_count,
                        skipped_count=skipped_count,
                        failure_count=len(failures),
                        extra=(
                            f"requests={request_count} "
                            f"window_trading_days={trading_days_by_frequency[frequency]}"
                        ),
                    )

        status = "partial" if failures else "success"
        if failures:
            error_message = "; ".join(
                f"{item['code']}({item['ts_code']} {item['frequency']}): {item['error']}"
                for item in failures[:20]
            )
            if len(failures) > 20:
                error_message += f"; ... {len(failures) - 20} more"
        return {
            "status": status,
            "stock_count": stock_count,
            "frequency_count": len(local_frequencies),
            "job_count": job_count,
            "request_count": request_count,
            "window_trading_days": trading_days_by_frequency,
            "skipped_count": skipped_count,
            "failure_count": len(failures),
            "failures": failures,
            "row_count": row_count,
            "output_root": str(output_root),
            "raw_output_root": str(raw_output_root) if write_raw and not dry_run else "",
            "error_message": error_message,
            "dry_run": dry_run,
            "backup_paths": backup_paths,
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
        result = run_minute_etl(
            token=args.token,
            codes=args.codes,
            codes_file=args.codes_file,
            all_stocks=args.all_stocks,
            stock_basic_path=args.stock_basic,
            frequencies=args.frequencies,
            start_date=args.start_date,
            end_date=args.end_date,
            trade_calendar_path=args.trade_calendar,
            window_trading_days=args.window_trading_days,
            window_days=args.window_days,
            output_root=args.output_root,
            raw_output_root=args.raw_output_root,
            write_raw=args.with_raw,
            limit_stocks=args.limit_stocks,
            dry_run=args.dry_run,
            write_log=not args.no_log,
            backup_root=args.backup_root,
            create_backup=args.create_backup,
            resume=args.resume,
            request_interval=args.request_interval,
            progress_every=args.progress_every,
            max_retries=args.max_retries,
            retry_interval=args.retry_interval,
            stop_on_error=args.stop_on_error,
        )
        if args.dry_run:
            print(
                f"Dry run converted {result['row_count']} rows "
                f"for {result['job_count']} stock/frequency jobs "
                f"({result['skipped_count']} skipped, {result['failure_count']} failed, "
                f"{result['request_count']} requests)."
            )
        else:
            print(
                f"Wrote {result['row_count']} rows for {result['job_count']} stock/frequency jobs "
                f"to {args.output_root} "
                f"({result['skipped_count']} skipped, {result['failure_count']} failed, "
                f"{result['request_count']} requests)."
            )
        if args.with_raw and not args.dry_run:
            print(f"Wrote raw Tushare rows to {args.raw_output_root}")
        for backup_path in result["backup_paths"]:
            print(f"Backed up previous file to {backup_path}")
        if result["failures"]:
            print("Failures:", file=sys.stderr)
            for item in result["failures"][:20]:
                print(
                    f"  {item['code']} ({item['ts_code']} {item['frequency']}): {item['error']}",
                    file=sys.stderr,
                )
            if len(result["failures"]) > 20:
                print(f"  ... {len(result['failures']) - 20} more", file=sys.stderr)
            return 1
        return 0
    except Exception as exc:
        print(f"fetch_minute failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
