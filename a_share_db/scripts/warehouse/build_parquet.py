#!/usr/bin/env python3
"""Build Parquet files from local formal CSV outputs.

CSV remains the fetch/resume layer. Parquet is the formal analysis layer built
from completed local CSV files.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.daily import ADJUST_TYPES
from a_share_db.constant.daily import ADJ_FACTOR_COLUMNS, DAILY_PRICE_COLUMNS
from a_share_db.constant.minute import MINUTE_FREQUENCIES
from a_share_db.constant.minute import MINUTE_BAR_COLUMNS
from a_share_db.constant.paths import (
    ADJ_FACTOR_ROOT,
    BACKUP_ROOT,
    DAILY_ROOT,
    ETL_LOG_PATH,
    MINUTE_ROOT,
    PARQUET_ADJ_FACTOR_ROOT,
    PARQUET_DAILY_ROOT,
    PARQUET_METADATA_ROOT,
    PARQUET_MINUTE_ROOT,
    STOCK_BASIC_PATH,
    TRADE_CALENDAR_PATH,
    build_data_backup_path,
)
from a_share_db.constant.stock_basic import STOCK_BASIC_COLUMNS
from a_share_db.constant.trade_calendar import TRADE_CALENDAR_COLUMNS
from a_share_db.constant.warehouse import PARQUET_ALL_TABLES, PARQUET_TABLES
from a_share_db.scripts.market.fetch_daily import load_requested_codes
from a_share_db.utils.progress import ProgressReporter


# Defaults keep the Parquet builder aligned with the project data layout.
DEFAULT_LOG = ETL_LOG_PATH
DEFAULT_BACKUP_ROOT = BACKUP_ROOT
DEFAULT_COMPRESSION = "zstd"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Parquet files from local CSV data files."
    )
    parser.add_argument(
        "--tables",
        nargs="+",
        choices=PARQUET_TABLES + PARQUET_ALL_TABLES,
        default=["metadata", "daily", "adj_factor"],
        help="Tables to build. Default: metadata daily adj_factor. Use all to include minute.",
    )
    parser.add_argument(
        "--codes",
        nargs="+",
        help="Local 6-digit stock codes to build for per-stock tables.",
    )
    parser.add_argument(
        "--codes-file",
        type=Path,
        help="Text file with one local 6-digit stock code per line.",
    )
    parser.add_argument(
        "--adjust-types",
        nargs="+",
        choices=ADJUST_TYPES,
        default=ADJUST_TYPES,
        help="Daily/minute adjust types to build. Default: none qfq hfq.",
    )
    parser.add_argument(
        "--frequencies",
        nargs="+",
        choices=MINUTE_FREQUENCIES,
        default=MINUTE_FREQUENCIES,
        help="Minute frequencies to build. Default: all supported frequencies.",
    )
    parser.add_argument(
        "--compression",
        default=DEFAULT_COMPRESSION,
        help=f"Parquet compression codec. Default: {DEFAULT_COMPRESSION}.",
    )
    parser.add_argument(
        "--limit-files",
        type=int,
        help="Build only the first N discovered CSV files. Useful for smoke tests.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Discover and read CSV files, but do not write Parquet files or logs.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip Parquet files that already exist and are non-empty.",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=100,
        help="Print progress every N files. Use 0 to disable progress output. Default: 100.",
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
        help=f"Backup directory for existing Parquet files. Default: {DEFAULT_BACKUP_ROOT}",
    )
    parser.add_argument(
        "--backup",
        dest="create_backup",
        action="store_true",
        help="Move existing output files to backups before replacing them. Default: off.",
    )
    parser.set_defaults(create_backup=False)
    return parser.parse_args()


def import_pandas():
    try:
        import pandas as pd
    except ImportError as exc:
        raise SystemExit("Missing dependency. Install with: python -m pip install pandas") from exc
    return pd


def ensure_parquet_engine() -> None:
    """Fail early with a clear install hint before any conversion work starts."""
    try:
        import pyarrow  # noqa: F401
    except ImportError as exc:
        raise SystemExit("Missing dependency. Install with: python -m pip install pyarrow") from exc


def normalize_tables(tables: Iterable[str]) -> list[str]:
    values = list(tables)
    if "all" in values:
        # all is a local shortcut, not a table name.
        return PARQUET_TABLES.copy()
    normalized = []
    seen = set()
    for value in values:
        if value not in seen:
            # Keep caller order and avoid duplicate table work.
            normalized.append(value)
            seen.add(value)
    return normalized


def select_code_paths(paths: list[Path], codes: list[str]) -> list[Path]:
    if not codes:
        return paths
    wanted = set(codes)
    # Per-stock CSV files use code as the filename stem.
    return [path for path in paths if path.stem in wanted]


def discover_csv_jobs(
    tables: Iterable[str],
    codes: list[str],
    adjust_types: Iterable[str],
    frequencies: Iterable[str],
) -> list[tuple[str, Path, Path]]:
    """Return conversion jobs as (table, input_csv, output_parquet)."""
    jobs: list[tuple[str, Path, Path]] = []
    selected_tables = set(tables)

    if "metadata" in selected_tables:
        # Metadata tables are single project-level files.
        metadata_jobs = [
            ("metadata", STOCK_BASIC_PATH, PARQUET_METADATA_ROOT / "stock_basic.parquet"),
            ("metadata", TRADE_CALENDAR_PATH, PARQUET_METADATA_ROOT / "trade_calendar.parquet"),
        ]
        jobs.extend(job for job in metadata_jobs if job[1].exists())

    if "daily" in selected_tables:
        for adjust_type in adjust_types:
            input_root = DAILY_ROOT / adjust_type
            output_root = PARQUET_DAILY_ROOT / adjust_type
            # Daily CSV files are stored one stock per file.
            paths = sorted(input_root.glob("*.csv"))
            for path in select_code_paths(paths, codes):
                jobs.append(("daily", path, output_root / f"{path.stem}.parquet"))

    if "adj_factor" in selected_tables:
        paths = sorted(ADJ_FACTOR_ROOT.glob("*.csv"))
        for path in select_code_paths(paths, codes):
            jobs.append(("adj_factor", path, PARQUET_ADJ_FACTOR_ROOT / f"{path.stem}.parquet"))

    if "minute" in selected_tables:
        for frequency in frequencies:
            for adjust_type in adjust_types:
                input_root = MINUTE_ROOT / frequency / adjust_type
                output_root = PARQUET_MINUTE_ROOT / frequency / adjust_type
                # Minute files stay per-stock to match the current fetch/resume layer.
                paths = sorted(input_root.glob("*.csv"))
                for path in select_code_paths(paths, codes):
                    jobs.append(("minute", path, output_root / f"{path.stem}.parquet"))

    return jobs


SCHEMA_COLUMNS = {
    "stock_basic": STOCK_BASIC_COLUMNS,
    "trade_calendar": TRADE_CALENDAR_COLUMNS,
    "daily": DAILY_PRICE_COLUMNS,
    "adj_factor": ADJ_FACTOR_COLUMNS,
    "minute": MINUTE_BAR_COLUMNS,
}

PROVIDER_ONLY_COLUMNS = {
    "ts_code",
    "symbol",
    "cal_date",
    "is_open",
    "pretrade_date",
    "trade_time",
    "vol",
    "freq",
}


def schema_name_for_job(table: str, path: Path) -> str:
    if table == "metadata":
        return path.stem
    return table


def validate_and_order_columns(frame, schema_name: str, path: Path):
    expected = SCHEMA_COLUMNS[schema_name]
    provider_columns = sorted(PROVIDER_ONLY_COLUMNS.intersection(frame.columns))
    if provider_columns:
        raise ValueError(
            "formal CSV contains provider-only columns: " + ", ".join(provider_columns)
        )

    missing = [column for column in expected if column not in frame.columns]
    if missing:
        raise ValueError(f"{path} missing columns: {', '.join(missing)}")

    extra = [column for column in frame.columns if column not in expected]
    if extra:
        raise ValueError(f"{path} has unexpected columns: {', '.join(extra)}")

    return frame[expected]


def read_csv_for_table(table: str, path: Path):
    pd = import_pandas()
    schema_name = schema_name_for_job(table, path)
    dtype = {}
    if schema_name in {"stock_basic", "daily", "adj_factor", "minute"}:
        dtype["code"] = str
    if schema_name in {"daily", "adj_factor", "minute"}:
        dtype["trade_date"] = str
    if schema_name == "minute":
        dtype["bar_end_time"] = str
    if schema_name == "trade_calendar":
        dtype["calendar_date"] = str
        dtype["previous_trade_date"] = str
    if schema_name == "stock_basic":
        dtype["list_date"] = str
        dtype["delist_date"] = str
    # Read code/date columns as strings first so normalization is explicit.
    frame = pd.read_csv(path, dtype=dtype).fillna("")
    frame = validate_and_order_columns(frame, schema_name, path)
    return normalize_frame(schema_name, frame)


def normalize_frame(schema_name: str, frame):
    pd = import_pandas()
    if "code" in frame.columns:
        # Formal Parquet keeps local six-digit stock codes.
        frame["code"] = frame["code"].astype(str).str.split(".").str[0].str.zfill(6)

    for column in ["trade_date", "calendar_date", "previous_trade_date", "list_date", "delist_date"]:
        if column not in frame.columns:
            continue
        # Store dates as real Parquet date values for better query behavior.
        frame[column] = pd.to_datetime(frame[column], errors="coerce").dt.date
    if "bar_end_time" in frame.columns:
        # Minute timestamps stay as Parquet timestamp values.
        frame["bar_end_time"] = pd.to_datetime(frame["bar_end_time"], errors="coerce")

    numeric_columns_by_table = {
        "daily": ["open", "high", "low", "close", "pre_close", "change", "pct_chg", "volume", "amount"],
        "adj_factor": ["adjust_factor"],
        "minute": ["open", "high", "low", "close", "volume", "amount"],
    }
    for column in numeric_columns_by_table.get(schema_name, []):
        if column in frame.columns:
            # Numeric columns compress better and query faster in Parquet.
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if schema_name == "trade_calendar" and "is_trading_day" in frame.columns:
        frame["is_trading_day"] = pd.to_numeric(frame["is_trading_day"], errors="coerce").astype(
            "Int64"
        )
    return frame


def write_parquet(
    frame,
    path: Path,
    compression: str = DEFAULT_COMPRESSION,
    backup_root: Path = DEFAULT_BACKUP_ROOT,
    backup_timestamp: str | None = None,
    create_backup: bool = False,
) -> Path | None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    backup_path = None

    try:
        frame.to_parquet(temp_path, index=False, compression=compression)

        # Backups are opt-in; temp replacement prevents partial formal files.
        if create_backup and path.exists():
            backup_timestamp = backup_timestamp or build_backup_timestamp()
            backup_path = build_backup_path(path, backup_root, backup_timestamp)
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            path.replace(backup_path)

        temp_path.replace(path)
    except Exception:
        # Restore the previous file if replacement fails after backup.
        if backup_path and backup_path.exists() and not path.exists():
            backup_path.replace(path)
        if temp_path.exists():
            temp_path.unlink()
        raise
    return backup_path


def build_backup_timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def build_backup_path(path: Path, backup_root: Path, backup_timestamp: str) -> Path:
    return build_data_backup_path(path, backup_root, backup_timestamp)


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
                "job_name": "build_parquet",
                "source": "local_csv",
                "start_time": start_time,
                "end_time": end_time,
                "status": status,
                "row_count": row_count,
                "error_message": error_message,
            }
        )


def run_build_parquet(
    tables: Iterable[str] = ("metadata", "daily", "adj_factor"),
    codes: Iterable[str] | None = None,
    codes_file: Path | None = None,
    adjust_types: Iterable[str] = ADJUST_TYPES,
    frequencies: Iterable[str] = MINUTE_FREQUENCIES,
    compression: str = DEFAULT_COMPRESSION,
    limit_files: int | None = None,
    dry_run: bool = False,
    resume: bool = False,
    progress_every: int = 0,
    write_log: bool = True,
    log_path: Path = DEFAULT_LOG,
    backup_root: Path = DEFAULT_BACKUP_ROOT,
    create_backup: bool = False,
) -> dict:
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row_count = 0
    file_count = 0
    skipped_count = 0
    failures: list[dict[str, str]] = []
    backup_paths: list[str] = []
    status = "failed"
    error_message = ""
    backup_timestamp = build_backup_timestamp()

    try:
        ensure_parquet_engine()
        selected_tables = normalize_tables(tables)
        selected_codes = load_requested_codes(codes, codes_file)
        # Discover all work before converting so progress has a stable total.
        jobs = discover_csv_jobs(selected_tables, selected_codes, adjust_types, frequencies)
        if limit_files is not None:
            if limit_files < 0:
                raise ValueError("limit-files must be greater than or equal to 0.")
            jobs = jobs[:limit_files]

        progress = ProgressReporter(len(jobs), every=progress_every, label="Build parquet")

        for index, (table, csv_path, parquet_path) in enumerate(jobs, start=1):
            try:
                if resume and parquet_path.exists() and parquet_path.stat().st_size > 0:
                    # Resume skips completed Parquet files, matching CSV fetch behavior.
                    skipped_count += 1
                    continue

                frame = read_csv_for_table(table, csv_path)
                row_count += len(frame)
                file_count += 1

                if not dry_run:
                    # Parquet is written atomically so readers never see a partial file.
                    backup_path = write_parquet(
                        frame,
                        parquet_path,
                        compression=compression,
                        backup_root=Path(backup_root),
                        backup_timestamp=backup_timestamp,
                        create_backup=create_backup,
                    )
                    if backup_path:
                        backup_paths.append(str(backup_path))
            except Exception as exc:
                # Keep long conversions running and report all bad files at the end.
                failures.append({"table": table, "path": str(csv_path), "error": str(exc)})
                continue
            finally:
                progress.maybe_print(
                    index,
                    row_count=row_count,
                    skipped_count=skipped_count,
                    failure_count=len(failures),
                )

        status = "partial" if failures else "success"
        if failures:
            # Keep log messages bounded when many files fail.
            error_message = "; ".join(
                f"{item['table']} {item['path']}: {item['error']}" for item in failures[:20]
            )
            if len(failures) > 20:
                error_message += f"; ... {len(failures) - 20} more"

        return {
            "status": status,
            "file_count": file_count,
            "job_count": len(jobs),
            "skipped_count": skipped_count,
            "failure_count": len(failures),
            "failures": failures,
            "row_count": row_count,
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
    try:
        result = run_build_parquet(
            tables=args.tables,
            codes=args.codes,
            codes_file=args.codes_file,
            adjust_types=args.adjust_types,
            frequencies=args.frequencies,
            compression=args.compression,
            limit_files=args.limit_files,
            dry_run=args.dry_run,
            resume=args.resume,
            progress_every=args.progress_every,
            write_log=not args.no_log,
            backup_root=args.backup_root,
            create_backup=args.create_backup,
        )
        action = "Dry run converted" if args.dry_run else "Built"
        print(
            f"{action} {result['file_count']} of {result['job_count']} files "
            f"({result['skipped_count']} skipped, {result['failure_count']} failed, "
            f"{result['row_count']} rows)."
        )
        for backup_path in result["backup_paths"]:
            print(f"Backed up previous file to {backup_path}")
        if result["failures"]:
            print("Failures:", file=sys.stderr)
            for item in result["failures"][:20]:
                print(f"  {item['table']} {item['path']}: {item['error']}", file=sys.stderr)
            if len(result["failures"]) > 20:
                print(f"  ... {len(result['failures']) - 20} more", file=sys.stderr)
            return 1
        return 0
    except Exception as exc:
        print(f"build_parquet failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
