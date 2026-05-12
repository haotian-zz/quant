#!/usr/bin/env python3
"""Fetch A-share stock metadata from Tushare.

Outputs the metadata tables defined in DESIGN.md:
data/metadata/stock_basic.csv
data/metadata/raw_tushare_stock_basic.csv
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.stock_basic import (
    DEFAULT_TUSHARE_LIST_STATUSES,
    STOCK_BASIC_COLUMNS,
    TUSHARE_LIST_STATUS_MAP,
    TUSHARE_STOCK_BASIC_FIELDS,
)
from a_share_db.constant.paths import (
    BACKUP_ROOT,
    ETL_LOG_PATH,
    RAW_TUSHARE_STOCK_BASIC_PATH,
    STOCK_BASIC_PATH,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = STOCK_BASIC_PATH
DEFAULT_RAW_OUTPUT = RAW_TUSHARE_STOCK_BASIC_PATH
DEFAULT_LOG = ETL_LOG_PATH
DEFAULT_BACKUP_ROOT = BACKUP_ROOT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Tushare stock_basic data and build data/metadata/stock_basic.csv."
    )
    parser.add_argument(
        "--token",
        default=os.getenv("TUSHARE_TOKEN"),
        help="Tushare token. Defaults to env var TUSHARE_TOKEN.",
    )
    parser.add_argument(
        "--statuses",
        nargs="+",
        default=DEFAULT_TUSHARE_LIST_STATUSES,
        help="Tushare list_status values to fetch. Default: L D P G.",
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
        help="Also write the raw Tushare stock_basic CSV.",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Do not append execution status to data/logs/etl_log.csv.",
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


def fetch_from_tushare(token: str, statuses: Iterable[str]):
    pd = import_pandas()
    ts = import_tushare()
    ts.set_token(token)
    pro = ts.pro_api()

    # Fetch each status separately because Tushare stock_basic takes one status.
    frames = []
    errors = []
    fields = ",".join(TUSHARE_STOCK_BASIC_FIELDS)
    for status in statuses:
        normalized_status = status.strip().upper()
        if not normalized_status:
            continue
        try:
            frame = pro.stock_basic(
                exchange="",
                list_status=normalized_status,
                fields=fields,
            )
        except Exception as exc:  # Tushare raises broad exceptions for API errors.
            errors.append(f"{normalized_status}: {exc}")
            continue

        if frame is not None and not frame.empty:
            frames.append(frame)

    if not frames:
        raise RuntimeError("No stock_basic rows fetched. " + "; ".join(errors))

    raw = pd.concat(frames, ignore_index=True)
    # Add missing columns defensively so schema conversion stays stable.
    for column in TUSHARE_STOCK_BASIC_FIELDS:
        if column not in raw.columns:
            raw[column] = ""

    raw = raw[TUSHARE_STOCK_BASIC_FIELDS].drop_duplicates(subset=["ts_code"], keep="last")
    return raw, errors


def convert_tushare_stock_basic(raw):
    """Convert raw Tushare stock_basic rows into the local stock master schema."""
    pd = import_pandas()
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    output = pd.DataFrame()

    raw_code = raw["symbol"].fillna("").astype(str).str.strip()
    missing_code = raw_code.eq("") | raw_code.str.lower().isin({"nan", "none", "nat"})
    output["code"] = raw_code.str.zfill(6)
    # ts_code is only used as a fallback; it is not stored in the curated table.
    output.loc[missing_code, "code"] = (
        raw.loc[missing_code, "ts_code"].fillna("").astype(str).str.split(".").str[0]
    )

    output["name"] = raw["name"].fillna("")
    output["full_name"] = raw["fullname"].fillna("")
    output["english_name"] = raw["enname"].fillna("")
    output["pinyin"] = raw["cnspell"].fillna("")
    output["exchange"] = raw["exchange"].fillna("").astype(str).str.upper()
    output["board"] = raw["market"].fillna("")
    output["industry"] = raw["industry"].fillna("")
    output["region"] = raw["area"].fillna("")
    output["currency"] = raw["curr_type"].fillna("")
    output["list_date"] = raw["list_date"].map(format_tushare_date)
    output["delist_date"] = raw["delist_date"].map(format_tushare_date)
    raw_list_status = raw["list_status"].fillna("").astype(str).str.upper()
    output["status"] = (
        raw_list_status.map(TUSHARE_LIST_STATUS_MAP).fillna(raw_list_status)
    )
    output["is_stock_connect"] = raw["is_hs"].fillna("")
    output["actual_controller"] = raw["act_name"].fillna("")
    output["controller_entity_type"] = raw["act_ent_type"].fillna("")
    output["update_time"] = update_time

    output = output[STOCK_BASIC_COLUMNS]
    output = output[output["code"].str.fullmatch(r"\d{6}", na=False)]
    output = output.sort_values(["exchange", "code"], kind="stable")
    return output


def format_tushare_date(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text.lower() in {"nan", "nat", "none"}:
        return ""
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

    # Backups are opt-in. By default the temp file replaces the target directly.
    if create_backup and path.exists():
        backup_timestamp = backup_timestamp or build_backup_timestamp()
        backup_path = build_backup_path(path, backup_root, backup_timestamp)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        path.replace(backup_path)

    try:
        # Replace only after the full temp file is written.
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
        # External paths are still backed up under backup_root without escaping it.
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
                "job_name": "fetch_stock_basic",
                "source": "tushare",
                "start_time": start_time,
                "end_time": end_time,
                "status": status,
                "row_count": row_count,
                "error_message": error_message,
            }
        )


def run_stock_basic_etl(
    token: str,
    statuses: Iterable[str] = DEFAULT_TUSHARE_LIST_STATUSES,
    output: Path = DEFAULT_OUTPUT,
    raw_output: Path = DEFAULT_RAW_OUTPUT,
    write_raw: bool = False,
    write_log: bool = True,
    log_path: Path = DEFAULT_LOG,
    limit: int | None = None,
    dry_run: bool = False,
    backup_root: Path = DEFAULT_BACKUP_ROOT,
    create_backup: bool = False,
) -> dict:
    """Fetch stock metadata and write local CSV outputs.

    This is the import-friendly API. The command-line entrypoint delegates here.
    """
    if not token:
        raise ValueError("Tushare token is required.")

    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row_count = 0
    status = "failed"
    error_message = ""
    backup_timestamp = build_backup_timestamp()
    backup_paths = []

    try:
        raw, fetch_errors = fetch_from_tushare(token, statuses)
        normalized = convert_tushare_stock_basic(raw)
        total_row_count = len(normalized)

        # Limit is for smoke tests, after conversion has proved the full schema works.
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
        result = run_stock_basic_etl(
            token=args.token,
            statuses=args.statuses,
            output=args.output,
            raw_output=args.raw_output,
            write_raw=args.with_raw,
            write_log=not args.no_log,
            limit=args.limit,
            dry_run=args.dry_run,
            backup_root=args.backup_root,
            create_backup=args.create_backup,
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
        print(f"fetch_stock_basic failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
