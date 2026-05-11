#!/usr/bin/env python3
"""Fetch exchange trade calendars from Tushare.

Outputs the metadata tables defined in DESIGN.md:
metadata/trade_calendar.csv
metadata/raw_tushare_trade_calendar.csv
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.trade_calendar import (
    ALL_TRADE_CAL_EXCHANGES,
    DEFAULT_A_SHARE_EXCHANGES,
    TRADE_CALENDAR_COLUMNS,
    TUSHARE_TRADE_CALENDAR_FIELDS,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "metadata" / "trade_calendar.csv"
DEFAULT_RAW_OUTPUT = PROJECT_ROOT / "metadata" / "raw_tushare_trade_calendar.csv"
DEFAULT_LOG = PROJECT_ROOT / "logs" / "etl_log.csv"
DEFAULT_BACKUP_ROOT = PROJECT_ROOT / "backups"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Tushare trade_cal data and build metadata/trade_calendar.csv."
    )
    parser.add_argument(
        "--token",
        default=os.getenv("TUSHARE_TOKEN"),
        help="Tushare token. Defaults to env var TUSHARE_TOKEN.",
    )
    parser.add_argument(
        "--exchanges",
        nargs="+",
        default=DEFAULT_A_SHARE_EXCHANGES,
        help="Exchange values to fetch. Use ALL for every supported exchange. Default: SSE SZSE.",
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
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Normalized output CSV path. Default: {DEFAULT_OUTPUT}",
    )
    parser.add_argument(
        "--raw-output",
        type=Path,
        default=DEFAULT_RAW_OUTPUT,
        help=f"Raw Tushare output CSV path when --with-raw is set. Default: {DEFAULT_RAW_OUTPUT}",
    )
    parser.add_argument(
        "--with-raw",
        action="store_true",
        help="Also write the raw Tushare trade_cal CSV.",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Do not append execution status to logs/etl_log.csv.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Write only the first N normalized rows. Useful for smoke tests.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and convert data, but do not write CSV files or logs.",
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


def import_tushare():
    try:
        import tushare as ts
    except ImportError as exc:
        raise SystemExit("Missing dependency. Install with: python -m pip install tushare") from exc
    return ts


def fetch_from_tushare(
    token: str,
    exchanges: Iterable[str],
    start_date: str | None = None,
    end_date: str | None = None,
):
    pd = import_pandas()
    ts = import_tushare()
    ts.set_token(token)
    pro = ts.pro_api()

    frames = []
    errors = []
    fields = ",".join(TUSHARE_TRADE_CALENDAR_FIELDS)
    for exchange in exchanges:
        normalized_exchange = exchange.strip().upper()
        if not normalized_exchange:
            continue
        try:
            frame = pro.trade_cal(
                exchange=normalized_exchange,
                start_date=start_date or None,
                end_date=end_date or None,
                fields=fields,
            )
        except Exception as exc:  # Tushare raises broad exceptions for API errors.
            errors.append(f"{normalized_exchange}: {exc}")
            continue

        if frame is not None and not frame.empty:
            for column in TUSHARE_TRADE_CALENDAR_FIELDS:
                if column not in frame.columns:
                    frame[column] = ""
            frame["exchange"] = frame["exchange"].fillna("")
            missing_exchange = frame["exchange"].astype(str).str.strip().eq("")
            frame.loc[missing_exchange, "exchange"] = normalized_exchange
            frames.append(frame[TUSHARE_TRADE_CALENDAR_FIELDS])

    if not frames:
        raise RuntimeError("No trade_cal rows fetched. " + "; ".join(errors))

    raw = pd.concat(frames, ignore_index=True)
    raw = raw[TUSHARE_TRADE_CALENDAR_FIELDS].drop_duplicates(
        subset=["exchange", "cal_date"],
        keep="last",
    )
    raw = raw.sort_values(["exchange", "cal_date"], kind="stable")
    return raw, errors


def normalize_exchange_args(exchanges: Iterable[str]) -> list[str]:
    normalized = []
    for exchange in exchanges:
        value = exchange.strip().upper()
        if not value:
            continue
        if value == "ALL":
            return ALL_TRADE_CAL_EXCHANGES.copy()
        normalized.append(value)
    return normalized or DEFAULT_A_SHARE_EXCHANGES.copy()


def convert_tushare_trade_calendar(raw):
    """Convert raw Tushare trade_cal rows into the local trade calendar schema."""
    pd = import_pandas()
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    output = pd.DataFrame()

    output["exchange"] = raw["exchange"].fillna("").astype(str).str.strip().str.upper()
    output["calendar_date"] = raw["cal_date"].map(format_tushare_date)
    output["is_trading_day"] = raw["is_open"].map(normalize_trading_day_flag)
    output["previous_trade_date"] = raw["pretrade_date"].map(format_tushare_date)
    output["update_time"] = update_time

    output = output[TRADE_CALENDAR_COLUMNS]
    output = output[output["exchange"].ne("")]
    output = output[output["calendar_date"].str.fullmatch(r"\d{4}-\d{2}-\d{2}", na=False)]
    output = output.sort_values(["exchange", "calendar_date"], kind="stable")
    return output


def normalize_trading_day_flag(value) -> str:
    text = str(value).strip()
    if text in {"1", "1.0", "True", "true"}:
        return "1"
    if text in {"0", "0.0", "False", "false"}:
        return "0"
    return text


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
    create_backup: bool = True,
) -> Path | None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temp_path, index=False, encoding="utf-8", lineterminator="\n")
    backup_path = None

    if create_backup and path.exists():
        backup_timestamp = backup_timestamp or build_backup_timestamp()
        backup_path = build_backup_path(path, backup_root, backup_timestamp)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        path.replace(backup_path)

    try:
        temp_path.replace(path)
    except Exception:
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
                "job_name": "fetch_trade_calendar",
                "source": "tushare",
                "start_time": start_time,
                "end_time": end_time,
                "status": status,
                "row_count": row_count,
                "error_message": error_message,
            }
        )


def run_trade_calendar_etl(
    token: str,
    exchanges: Iterable[str] = ("SSE",),
    start_date: str | None = None,
    end_date: str | None = None,
    output: Path = DEFAULT_OUTPUT,
    raw_output: Path = DEFAULT_RAW_OUTPUT,
    write_raw: bool = False,
    write_log: bool = True,
    log_path: Path = DEFAULT_LOG,
    limit: int | None = None,
    dry_run: bool = False,
    backup_root: Path = DEFAULT_BACKUP_ROOT,
    create_backup: bool = True,
) -> dict:
    """Fetch trade calendars and write local CSV outputs."""
    if not token:
        raise ValueError("Tushare token is required.")

    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row_count = 0
    status = "failed"
    error_message = ""
    backup_timestamp = build_backup_timestamp()
    backup_paths = []

    try:
        raw, fetch_errors = fetch_from_tushare(
            token,
            normalize_exchange_args(exchanges),
            start_date,
            end_date,
        )
        normalized = convert_tushare_trade_calendar(raw)
        total_row_count = len(normalized)

        if limit is not None:
            if limit < 0:
                raise ValueError("limit must be greater than or equal to 0.")
            normalized = normalized.head(limit)
            raw = raw.head(limit)

        row_count = len(normalized)
        if not dry_run:
            backup_path = write_csv(
                normalized,
                Path(output),
                backup_root=Path(backup_root),
                backup_timestamp=backup_timestamp,
                create_backup=create_backup,
            )
            if backup_path:
                backup_paths.append(str(backup_path))

        if write_raw and not dry_run:
            backup_path = write_csv(
                raw,
                Path(raw_output),
                backup_root=Path(backup_root),
                backup_timestamp=backup_timestamp,
                create_backup=create_backup,
            )
            if backup_path:
                backup_paths.append(str(backup_path))

        if fetch_errors:
            status = "partial"
            error_message = "; ".join(fetch_errors)
        else:
            status = "success"

        return {
            "status": status,
            "row_count": row_count,
            "total_row_count": total_row_count,
            "output": str(output),
            "raw_output": str(raw_output) if write_raw and not dry_run else "",
            "error_message": error_message,
            "dry_run": dry_run,
            "limit": limit,
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
        result = run_trade_calendar_etl(
            token=args.token,
            exchanges=args.exchanges,
            start_date=args.start_date,
            end_date=args.end_date,
            output=args.output,
            raw_output=args.raw_output,
            write_raw=args.with_raw,
            write_log=not args.no_log,
            limit=args.limit,
            dry_run=args.dry_run,
            backup_root=args.backup_root,
            create_backup=not args.no_backup,
        )
        if args.dry_run:
            print(
                f"Dry run converted {result['row_count']} rows "
                f"from {result['total_row_count']} fetched normalized rows."
            )
        else:
            print(f"Wrote {result['row_count']} rows to {args.output}")
        if args.with_raw and not args.dry_run:
            print(f"Wrote raw Tushare rows to {args.raw_output}")
        for backup_path in result["backup_paths"]:
            print(f"Backed up previous file to {backup_path}")
        if result["error_message"]:
            print("Fetch warnings: " + result["error_message"], file=sys.stderr)
        return 0
    except Exception as exc:
        print(f"fetch_trade_calendar failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
