#!/usr/bin/env python3
"""Build adjusted daily prices from local none daily data and adj factors.

Outputs:
data/market_data/daily/qfq/{code}.csv
data/market_data/daily/hfq/{code}.csv
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

from a_share_db.constant.daily import ADJUST_TYPES, DAILY_PRICE_COLUMNS
from a_share_db.constant.paths import (
    ADJ_FACTOR_ROOT,
    BACKUP_ROOT,
    DAILY_NONE_ROOT,
    DAILY_ROOT,
    ETL_LOG_PATH,
    STOCK_BASIC_PATH,
)
from a_share_db.utils.progress import ProgressReporter


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STOCK_BASIC = STOCK_BASIC_PATH
DEFAULT_NONE_ROOT = DAILY_NONE_ROOT
DEFAULT_ADJ_FACTOR_ROOT = ADJ_FACTOR_ROOT
DEFAULT_OUTPUT_ROOT = DAILY_ROOT
DEFAULT_LOG = ETL_LOG_PATH
DEFAULT_BACKUP_ROOT = BACKUP_ROOT
ADJUSTED_TYPES = ["qfq", "hfq"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build qfq/hfq daily data from local none daily data and adj_factor data."
    )
    parser.add_argument(
        "--codes",
        nargs="+",
        help="Local 6-digit stock codes to build, for example 600519 000001.",
    )
    parser.add_argument(
        "--codes-file",
        type=Path,
        help="Text file with one local 6-digit stock code per line.",
    )
    parser.add_argument(
        "--all-stocks",
        action="store_true",
        help="Build every listed stock in data/metadata/stock_basic.csv.",
    )
    parser.add_argument(
        "--stock-basic",
        type=Path,
        default=DEFAULT_STOCK_BASIC,
        help=f"Local stock_basic.csv path. Default: {DEFAULT_STOCK_BASIC}",
    )
    parser.add_argument(
        "--adjust-types",
        nargs="+",
        choices=ADJUSTED_TYPES,
        default=ADJUSTED_TYPES,
        help="Adjusted price types to build. Default: qfq hfq.",
    )
    parser.add_argument(
        "--none-root",
        type=Path,
        default=DEFAULT_NONE_ROOT,
        help=f"Unadjusted daily input directory. Default: {DEFAULT_NONE_ROOT}",
    )
    parser.add_argument(
        "--adj-factor-root",
        type=Path,
        default=DEFAULT_ADJ_FACTOR_ROOT,
        help=f"Adj factor input directory. Default: {DEFAULT_ADJ_FACTOR_ROOT}",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help=f"Daily output root directory. Default: {DEFAULT_OUTPUT_ROOT}",
    )
    parser.add_argument(
        "--limit-stocks",
        type=int,
        help="Build only the first N selected stocks. Useful for smoke tests.",
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
        default=50,
        help="Print progress every N stocks. Use 0 to disable progress output. Default: 50.",
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


def read_stock_basic(path: Path):
    pd = import_pandas()
    if not path.exists():
        raise FileNotFoundError(f"Missing stock_basic file: {path}")
    frame = pd.read_csv(path, dtype=str).fillna("")
    required = {"code"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"stock_basic missing columns: {', '.join(sorted(missing))}")
    if "status" in frame.columns:
        # Adjusted tables are built for listed stocks by default.
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
            normalized.append(value)
            seen.add(value)
    return normalized


def select_codes(stock_basic, codes: list[str], all_stocks: bool, limit_stocks: int | None) -> list[str]:
    if not codes and not all_stocks:
        raise ValueError("Pass --codes, --codes-file, or --all-stocks.")
    if codes:
        available = set(stock_basic["code"])
        missing = [code for code in codes if code not in available]
        if missing:
            raise ValueError("Codes not found in stock_basic.csv: " + ", ".join(missing))
        selected = codes
    else:
        sort_columns = ["code"]
        if "exchange" in stock_basic.columns:
            sort_columns = ["exchange", "code"]
        selected = stock_basic.sort_values(sort_columns, kind="stable")["code"].tolist()

    if limit_stocks is not None:
        if limit_stocks < 0:
            raise ValueError("limit-stocks must be greater than or equal to 0.")
        selected = selected[:limit_stocks]
    return selected


def build_adjusted_daily(none_daily, adj_factor, adjust_type: str):
    if adjust_type not in ADJUST_TYPES or adjust_type == "none":
        raise ValueError(f"Unsupported adjusted type: {adjust_type}")

    pd = import_pandas()
    merged = none_daily.merge(
        adj_factor[["code", "trade_date", "adjust_factor"]],
        on=["code", "trade_date"],
        how="inner",
    )
    if merged.empty:
        return merged.reindex(columns=DAILY_PRICE_COLUMNS)

    # Align daily prices and factors by stock/date before applying formulas.
    merged = merged.sort_values(["code", "trade_date"], kind="stable").copy()
    merged["code"] = merged["code"].astype(str).str.zfill(6)
    price_columns = ["open", "high", "low", "close", "pre_close"]
    for column in price_columns + ["volume", "amount", "adjust_factor"]:
        merged[column] = pd.to_numeric(merged[column], errors="coerce")

    if adjust_type == "qfq":
        # qfq anchors all prices to the latest available adjustment factor.
        latest_factor = merged["adjust_factor"].dropna().iloc[-1]
        multiplier = merged["adjust_factor"] / latest_factor
    else:
        # hfq grows with the raw factor and can be appended for missing dates.
        multiplier = merged["adjust_factor"]

    for column in price_columns:
        merged[column] = merged[column] * multiplier

    # Recompute change fields after price adjustment.
    merged["change"] = merged["close"] - merged["pre_close"]
    merged["pct_chg"] = merged["change"] / merged["pre_close"] * 100
    merged["adjust_type"] = adjust_type
    merged["update_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return merged[DAILY_PRICE_COLUMNS]


def read_daily_inputs(code: str, none_root: Path, adj_factor_root: Path):
    pd = import_pandas()
    none_path = Path(none_root) / f"{code}.csv"
    adj_path = Path(adj_factor_root) / f"{code}.csv"
    if not none_path.exists():
        raise FileNotFoundError(f"Missing none daily file: {none_path}")
    if not adj_path.exists():
        raise FileNotFoundError(f"Missing adj_factor file: {adj_path}")
    return (
        pd.read_csv(none_path, dtype={"code": str, "trade_date": str}),
        pd.read_csv(adj_path, dtype={"code": str, "trade_date": str}),
    )


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
                "job_name": "build_adjusted_daily",
                "source": "local",
                "start_time": start_time,
                "end_time": end_time,
                "status": status,
                "row_count": row_count,
                "error_message": error_message,
            }
        )


def run_build_adjusted_daily(
    codes: Iterable[str] | None = None,
    codes_file: Path | None = None,
    all_stocks: bool = False,
    stock_basic_path: Path = DEFAULT_STOCK_BASIC,
    adjust_types: Iterable[str] = ADJUSTED_TYPES,
    none_root: Path = DEFAULT_NONE_ROOT,
    adj_factor_root: Path = DEFAULT_ADJ_FACTOR_ROOT,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    limit_stocks: int | None = None,
    dry_run: bool = False,
    write_log: bool = True,
    log_path: Path = DEFAULT_LOG,
    backup_root: Path = DEFAULT_BACKUP_ROOT,
    create_backup: bool = False,
    resume: bool = False,
    progress_every: int = 0,
    stop_on_error: bool = False,
) -> dict:
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
        stock_basic = read_stock_basic(Path(stock_basic_path))
        requested_codes = load_requested_codes(codes, codes_file)
        selected_codes = select_codes(stock_basic, requested_codes, all_stocks, limit_stocks)
        stock_count = len(selected_codes)
        progress = ProgressReporter(stock_count, every=progress_every, label="Build adjusted daily")

        for index, code in enumerate(selected_codes, start=1):
            try:
                none_daily, adj_factor = read_daily_inputs(code, Path(none_root), Path(adj_factor_root))
                for adjust_type in adjust_types:
                    output_path = Path(output_root) / adjust_type / f"{code}.csv"
                    if resume and output_path.exists() and output_path.stat().st_size > 0:
                        # Rebuild jobs can resume by skipping completed adjusted files.
                        skipped_count += 1
                        continue
                    adjusted = build_adjusted_daily(none_daily, adj_factor, adjust_type)
                    row_count += len(adjusted)
                    if dry_run:
                        continue
                    backup_path = write_csv(
                        adjusted,
                        output_path,
                        backup_root=Path(backup_root),
                        backup_timestamp=backup_timestamp,
                        create_backup=create_backup,
                    )
                    if backup_path:
                        backup_paths.append(str(backup_path))
            except Exception as exc:
                failures.append({"code": code, "error": str(exc)})
                if stop_on_error:
                    raise
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
            error_message = "; ".join(f"{item['code']}: {item['error']}" for item in failures[:20])
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
    try:
        result = run_build_adjusted_daily(
            codes=args.codes,
            codes_file=args.codes_file,
            all_stocks=args.all_stocks,
            stock_basic_path=args.stock_basic,
            adjust_types=args.adjust_types,
            none_root=args.none_root,
            adj_factor_root=args.adj_factor_root,
            output_root=args.output_root,
            limit_stocks=args.limit_stocks,
            dry_run=args.dry_run,
            write_log=not args.no_log,
            backup_root=args.backup_root,
            create_backup=args.create_backup,
            resume=args.resume,
            progress_every=args.progress_every,
            stop_on_error=args.stop_on_error,
        )
        if args.dry_run:
            print(
                f"Dry run built {result['row_count']} rows "
                f"for {result['stock_count']} stocks "
                f"({result['skipped_count']} skipped, {result['failure_count']} failed)."
            )
        else:
            print(
                f"Wrote {result['row_count']} rows for {result['stock_count']} stocks "
                f"to {args.output_root} "
                f"({result['skipped_count']} skipped, {result['failure_count']} failed)."
            )
        for backup_path in result["backup_paths"]:
            print(f"Backed up previous file to {backup_path}")
        if result["failures"]:
            print("Failures:", file=sys.stderr)
            for item in result["failures"][:20]:
                print(f"  {item['code']}: {item['error']}", file=sys.stderr)
            if len(result["failures"]) > 20:
                print(f"  ... {len(result['failures']) - 20} more", file=sys.stderr)
            return 1
        return 0
    except Exception as exc:
        print(f"build_adjusted_daily failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
