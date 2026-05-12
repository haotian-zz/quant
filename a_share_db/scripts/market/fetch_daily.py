#!/usr/bin/env python3
"""Fetch unadjusted A-share daily prices from Tushare.

Outputs:
data/market_data/daily/none/{code}.csv
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.daily import (
    DAILY_PRICE_COLUMNS,
    TUSHARE_AMOUNT_TO_LOCAL,
    TUSHARE_DAILY_FIELDS,
    TUSHARE_VOLUME_TO_LOCAL,
)
from a_share_db.constant.paths import (
    BACKUP_ROOT,
    DAILY_NONE_ROOT,
    ETL_LOG_PATH,
    RAW_TUSHARE_DAILY_NONE_ROOT,
    STOCK_BASIC_PATH,
)
from a_share_db.utils.progress import ProgressReporter
from a_share_db.utils.provider_codes import build_tushare_ts_code


# Defaults mirror the local data layout and keep CLI/import behavior aligned.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STOCK_BASIC = STOCK_BASIC_PATH
DEFAULT_OUTPUT_ROOT = DAILY_NONE_ROOT
DEFAULT_RAW_OUTPUT_ROOT = RAW_TUSHARE_DAILY_NONE_ROOT
DEFAULT_LOG = ETL_LOG_PATH
DEFAULT_BACKUP_ROOT = BACKUP_ROOT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Tushare daily data and build data/market_data/daily/none/{code}.csv."
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
        "--start-date",
        help="Start date in YYYYMMDD format. Defaults to provider behavior.",
    )
    parser.add_argument(
        "--end-date",
        help="End date in YYYYMMDD format. Defaults to provider behavior.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help=f"Output directory. Default: {DEFAULT_OUTPUT_ROOT}",
    )
    parser.add_argument(
        "--raw-output-root",
        type=Path,
        default=DEFAULT_RAW_OUTPUT_ROOT,
        help=f"Raw output directory when --with-raw is set. Default: {DEFAULT_RAW_OUTPUT_ROOT}",
    )
    parser.add_argument(
        "--with-raw",
        action="store_true",
        help="Also write raw Tushare daily CSV files.",
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
        help="Skip stocks whose output CSV already exists and is non-empty.",
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
        help="Maximum attempts per stock before recording a failure. Default: 3.",
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
        "--backup",
        dest="create_backup",
        action="store_true",
        help="Move existing output files to backups before replacing them. Default: off.",
    )
    parser.add_argument("--no-backup", dest="create_backup", action="store_false", help=argparse.SUPPRESS)
    parser.set_defaults(create_backup=False)
    return parser.parse_args()


def import_pandas():
    try:
        import pandas as pd
    except ImportError as exc:
        raise SystemExit("Missing dependency. Install with: python -m pip install pandas") from exc
    return pd


def import_tushare():
    try:
        import tushare as ts
    except ImportError as exc:
        raise SystemExit("Missing dependency. Install with: python -m pip install tushare") from exc
    return ts


def read_stock_basic(path: Path):
    pd = import_pandas()
    if not path.exists():
        raise FileNotFoundError(f"Missing stock_basic file: {path}")
    frame = pd.read_csv(path, dtype=str).fillna("")
    required = {"code", "name", "exchange"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"stock_basic missing columns: {', '.join(sorted(missing))}")
    if "status" in frame.columns:
        # Default daily jobs fetch listed stocks from the local stock master.
        frame = frame[frame["status"].eq("listed")]
    return frame


def load_requested_codes(codes: Iterable[str] | None, codes_file: Path | None) -> list[str]:
    selected = []
    if codes:
        selected.extend(codes)
    if codes_file:
        selected.extend(
            line.strip()
            for line in codes_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        )

    normalized = []
    seen = set()
    for code in selected:
        value = str(code).strip().split(".")[0].zfill(6)
        if value and value not in seen:
            # Keep input order but remove duplicates.
            normalized.append(value)
            seen.add(value)
    return normalized


def select_stock_rows(stock_basic, codes: list[str], all_stocks: bool, limit_stocks: int | None):
    if not codes and not all_stocks:
        raise ValueError("Pass --codes, --codes-file, or --all-stocks.")
    if codes:
        selected = stock_basic[stock_basic["code"].isin(codes)].copy()
        found = set(selected["code"])
        missing = [code for code in codes if code not in found]
        if missing:
            raise ValueError("Codes not found in stock_basic.csv: " + ", ".join(missing))
        # Preserve explicit caller order for focused test runs.
        selected["__order"] = selected["code"].map({code: index for index, code in enumerate(codes)})
        selected = selected.sort_values("__order", kind="stable").drop(columns=["__order"])
    else:
        # Full-market jobs use stable ordering so progress is repeatable.
        selected = stock_basic.sort_values(["exchange", "code"], kind="stable").copy()

    if limit_stocks is not None:
        if limit_stocks < 0:
            raise ValueError("limit-stocks must be greater than or equal to 0.")
        selected = selected.head(limit_stocks)
    return selected


def fetch_from_tushare(token: str, ts_code: str, start_date: str | None, end_date: str | None):
    # Tushare ts_code is generated only for the provider request.
    # The formal table keeps the local six-digit code.
    ts = import_tushare()
    ts.set_token(token)
    pro = ts.pro_api()
    frame = pro.daily(
        ts_code=ts_code,
        start_date=start_date or None,
        end_date=end_date or None,
        fields=",".join(TUSHARE_DAILY_FIELDS),
    )
    pd = import_pandas()
    if frame is None:
        frame = pd.DataFrame(columns=TUSHARE_DAILY_FIELDS)
    # Keep downstream conversion independent from provider column omissions.
    for column in TUSHARE_DAILY_FIELDS:
        if column not in frame.columns:
            frame[column] = ""
    return frame[TUSHARE_DAILY_FIELDS]


def fetch_with_retries(
    token: str,
    ts_code: str,
    start_date: str | None,
    end_date: str | None,
    max_retries: int,
    retry_interval: float,
):
    if max_retries < 1:
        raise ValueError("max-retries must be greater than or equal to 1.")
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            return fetch_from_tushare(token, ts_code, start_date, end_date)
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                # Retry transient provider or network failures before marking the stock failed.
                time.sleep(retry_interval)
    raise last_error


def convert_tushare_daily(raw, name_by_code: dict[str, str]):
    """Convert raw Tushare daily rows into the local unadjusted daily schema."""
    pd = import_pandas()
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    output = pd.DataFrame()

    output["code"] = raw["ts_code"].fillna("").astype(str).str.split(".").str[0].str.zfill(6)
    output["name"] = output["code"].map(name_by_code).fillna("")
    output["trade_date"] = raw["trade_date"].map(format_tushare_date)
    output["open"] = raw["open"]
    output["high"] = raw["high"]
    output["low"] = raw["low"]
    output["close"] = raw["close"]
    output["pre_close"] = raw["pre_close"]
    output["change"] = raw["change"]
    output["pct_chg"] = raw["pct_chg"]
    # Convert provider units into local units: shares and yuan.
    output["volume"] = pd.to_numeric(raw["vol"], errors="coerce") * TUSHARE_VOLUME_TO_LOCAL
    output["amount"] = pd.to_numeric(raw["amount"], errors="coerce") * TUSHARE_AMOUNT_TO_LOCAL
    output["adjust_type"] = "none"
    output["update_time"] = update_time

    output = output[DAILY_PRICE_COLUMNS]
    # Drop malformed provider rows before writing the formal table.
    output = output[output["code"].str.fullmatch(r"\d{6}", na=False)]
    output = output[output["trade_date"].str.fullmatch(r"\d{4}-\d{2}-\d{2}", na=False)]
    output = output.sort_values(["code", "trade_date"], kind="stable")
    return output


def format_tushare_date(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text.lower() in {"nan", "nat", "none"}:
        return ""
    if text.endswith(".0"):
        text = text[:-2]
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    return text


def write_csv(
    frame,
    path: Path,
    backup_root: Path = DEFAULT_BACKUP_ROOT,
    backup_timestamp: str | None = None,
    create_backup: bool = False,
) -> Path | None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temp_path, index=False, encoding="utf-8", lineterminator="\n")
    backup_path = None

    # Backup is optional; temp replacement protects against partial writes.
    if create_backup and path.exists():
        backup_timestamp = backup_timestamp or build_backup_timestamp()
        backup_path = build_backup_path(path, backup_root, backup_timestamp)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        path.replace(backup_path)

    try:
        temp_path.replace(path)
    except Exception:
        # If replacement fails after moving the old file, restore it.
        if backup_path and backup_path.exists() and not path.exists():
            backup_path.replace(path)
        raise

    return backup_path


def build_backup_timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def build_backup_path(path: Path, backup_root: Path, backup_timestamp: str) -> Path:
    path = Path(path)
    try:
        relative_path = path.resolve().relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        # External output paths are still backed up under backup_root.
        if path.is_absolute():
            relative_path = Path("external").joinpath(*path.parts[1:])
        else:
            relative_path = path
    return Path(backup_root) / backup_timestamp / relative_path


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
                "job_name": "fetch_daily",
                "source": "tushare",
                "start_time": start_time,
                "end_time": end_time,
                "status": status,
                "row_count": row_count,
                "error_message": error_message,
            }
        )


def run_daily_etl(
    token: str,
    codes: Iterable[str] | None = None,
    codes_file: Path | None = None,
    all_stocks: bool = False,
    stock_basic_path: Path = DEFAULT_STOCK_BASIC,
    start_date: str | None = None,
    end_date: str | None = None,
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
    status = "failed"
    error_message = ""
    backup_timestamp = build_backup_timestamp()
    backup_paths = []
    stock_count = 0
    skipped_count = 0
    failures = []

    try:
        if request_interval < 0:
            raise ValueError("request-interval must be greater than or equal to 0.")
        if retry_interval < 0:
            raise ValueError("retry-interval must be greater than or equal to 0.")

        stock_basic = read_stock_basic(Path(stock_basic_path))
        selected_codes = load_requested_codes(codes, codes_file)
        stocks = select_stock_rows(stock_basic, selected_codes, all_stocks, limit_stocks)
        stock_count = len(stocks)
        name_by_code = dict(zip(stock_basic["code"], stock_basic["name"]))
        # Progress is per stock because each stock writes one daily file.
        progress = ProgressReporter(stock_count, every=progress_every, label="Fetch daily")

        for index, stock in enumerate(stocks.to_dict("records"), start=1):
            code = stock["code"]
            output_path = Path(output_root) / f"{code}.csv"
            ts_code = ""
            try:
                if resume and output_path.exists() and output_path.stat().st_size > 0:
                    # Full-history fetch can skip completed files when resume is enabled.
                    skipped_count += 1
                    progress.maybe_print(
                        index,
                        row_count=row_count,
                        skipped_count=skipped_count,
                        failure_count=len(failures),
                    )
                    continue

                ts_code = build_tushare_ts_code(code, stock.get("exchange", ""))
                raw = fetch_with_retries(
                    token,
                    ts_code,
                    start_date,
                    end_date,
                    max_retries=max_retries,
                    retry_interval=retry_interval,
                )
            except Exception as exc:
                # Keep long all-stock jobs running unless stop-on-error is requested.
                failures.append({"code": code, "ts_code": ts_code, "error": str(exc)})
                if stop_on_error:
                    raise
                progress.maybe_print(
                    index,
                    row_count=row_count,
                    skipped_count=skipped_count,
                    failure_count=len(failures),
                )
                continue

            normalized = convert_tushare_daily(raw, name_by_code)
            row_count += len(normalized)

            if not dry_run:
                # Formal output contains local fields and local units only.
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
                # Raw output is optional and keeps provider fields for debugging.
                backup_path = write_csv(
                    raw,
                    Path(raw_output_root) / f"{code}.csv",
                    backup_root=Path(backup_root),
                    backup_timestamp=backup_timestamp,
                    create_backup=create_backup,
                )
                if backup_path:
                    backup_paths.append(str(backup_path))

            if request_interval:
                # Keep long jobs from hammering the provider API.
                time.sleep(request_interval)
            progress.maybe_print(
                index,
                row_count=row_count,
                skipped_count=skipped_count,
                failure_count=len(failures),
            )

        status = "partial" if failures else "success"
        if failures:
            # Keep the returned error message bounded so logs remain readable.
            error_message = "; ".join(
                f"{item['code']}({item['ts_code']}): {item['error']}" for item in failures[:20]
            )
            if len(failures) > 20:
                error_message += f"; ... {len(failures) - 20} more"
        return {
            "status": status,
            "stock_count": stock_count,
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
        result = run_daily_etl(
            token=args.token,
            codes=args.codes,
            codes_file=args.codes_file,
            all_stocks=args.all_stocks,
            stock_basic_path=args.stock_basic,
            start_date=args.start_date,
            end_date=args.end_date,
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
                f"for {result['stock_count']} stocks "
                f"({result['skipped_count']} skipped, {result['failure_count']} failed)."
            )
        else:
            print(
                f"Wrote {result['row_count']} rows for {result['stock_count']} stocks "
                f"to {args.output_root} "
                f"({result['skipped_count']} skipped, {result['failure_count']} failed)."
            )
        if args.with_raw and not args.dry_run:
            print(f"Wrote raw Tushare rows to {args.raw_output_root}")
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
        print(f"fetch_daily failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
