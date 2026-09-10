#!/usr/bin/env python3
"""Fetch margin trading and securities lending data from Tushare.

Outputs:
data/market_data/margin/{code}.csv        (per-stock detail, --tables detail)
data/market_data/margin_summary.csv       (per-exchange totals, --tables summary)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.margin import (
    DEFAULT_MARGIN_START_DATE,
    MARGIN_COLUMNS,
    MARGIN_PAGE_SIZE,
    MARGIN_SUMMARY_COLUMNS,
    MARGIN_SUMMARY_EXCHANGES,
    TUSHARE_MARGIN_DETAIL_FIELD_MAP,
    TUSHARE_MARGIN_DETAIL_FIELDS,
    TUSHARE_MARGIN_SUMMARY_FIELD_MAP,
    TUSHARE_MARGIN_SUMMARY_FIELDS,
)
from a_share_db.constant.paths import MARGIN_ROOT, MARGIN_SUMMARY_PATH, RAW_TUSHARE_ROOT
from a_share_db.utils.cli import (
    add_date_range_arguments,
    add_run_control_arguments,
    add_stock_selection_arguments,
    add_token_argument,
    report_result,
    require_token,
    run_control_kwargs,
    stock_selection_kwargs,
)
from a_share_db.utils.etl_common import convert_mapped_frame, fetch_paginated, import_pandas
from a_share_db.utils.etl_runners import run_per_stock_etl, run_single_table_etl


DEFAULT_OUTPUT_ROOT = MARGIN_ROOT
DEFAULT_RAW_OUTPUT_ROOT = RAW_TUSHARE_ROOT / "margin"
DEFAULT_SUMMARY_OUTPUT = MARGIN_SUMMARY_PATH
DEFAULT_RAW_SUMMARY_OUTPUT = RAW_TUSHARE_ROOT / "margin_summary.csv"
MARGIN_TABLES = ["detail", "summary"]
DETAIL_FIELD_MAP = {"ts_code": "code", "trade_date": "trade_date", **TUSHARE_MARGIN_DETAIL_FIELD_MAP}
SUMMARY_FIELD_MAP = {"exchange_id": "exchange", "trade_date": "trade_date", **TUSHARE_MARGIN_SUMMARY_FIELD_MAP}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Tushare margin_detail (per stock) and margin (per exchange) data."
    )
    add_token_argument(parser)
    parser.add_argument("--tables", nargs="+", choices=MARGIN_TABLES, default=MARGIN_TABLES, help="Tables to fetch. Default: detail summary.")
    add_stock_selection_arguments(parser)
    add_date_range_arguments(parser, default_start=DEFAULT_MARGIN_START_DATE, end_defaults_to_today=True)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT, help=f"Per-stock output directory. Default: {DEFAULT_OUTPUT_ROOT}")
    parser.add_argument("--raw-output-root", type=Path, default=DEFAULT_RAW_OUTPUT_ROOT, help=f"Raw per-stock output when --with-raw is set. Default: {DEFAULT_RAW_OUTPUT_ROOT}")
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY_OUTPUT, help=f"Summary output CSV. Default: {DEFAULT_SUMMARY_OUTPUT}")
    parser.add_argument("--raw-summary-output", type=Path, default=DEFAULT_RAW_SUMMARY_OUTPUT, help=f"Raw summary output when --with-raw is set. Default: {DEFAULT_RAW_SUMMARY_OUTPUT}")
    parser.add_argument("--with-raw", action="store_true", help="Also write raw provider CSV files.")
    add_run_control_arguments(parser, incremental=True)
    return parser.parse_args()


def fetch_margin_detail(pro, ts_code: str, stock: dict, start_date: str | None, end_date: str | None):
    return fetch_paginated(
        pro,
        "margin_detail",
        TUSHARE_MARGIN_DETAIL_FIELDS,
        page_size=MARGIN_PAGE_SIZE,
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
    )


def convert_tushare_margin_detail(raw, stock: dict | None = None):
    """Convert raw Tushare margin_detail rows into the local margin schema."""
    return convert_mapped_frame(
        raw,
        DETAIL_FIELD_MAP,
        MARGIN_COLUMNS,
        sort_columns=["code", "trade_date"],
        date_columns=["trade_date"],
    )


def build_summary_fetcher(start_date: str | None, end_date: str | None):
    def fetch_margin_summary(pro):
        pd = import_pandas()
        frames = [
            fetch_paginated(
                pro,
                "margin",
                TUSHARE_MARGIN_SUMMARY_FIELDS,
                page_size=MARGIN_PAGE_SIZE,
                exchange_id=exchange,
                start_date=start_date,
                end_date=end_date,
            )
            for exchange in MARGIN_SUMMARY_EXCHANGES
        ]
        return pd.concat(frames, ignore_index=True)

    return fetch_margin_summary


def convert_tushare_margin_summary(raw):
    """Convert raw Tushare margin rows into the local margin_summary schema."""
    return convert_mapped_frame(
        raw,
        SUMMARY_FIELD_MAP,
        MARGIN_SUMMARY_COLUMNS,
        sort_columns=["exchange", "trade_date"],
        date_columns=["trade_date"],
        code_fields=(),
        code_column=None,
    )


def run_margin_etl(token: str, output_root: Path = DEFAULT_OUTPUT_ROOT, raw_output_root: Path = DEFAULT_RAW_OUTPUT_ROOT, **kwargs) -> dict:
    return run_per_stock_etl(
        "fetch_margin",
        token,
        fetch_margin_detail,
        convert_tushare_margin_detail,
        output_root=output_root,
        raw_output_root=raw_output_root,
        columns=MARGIN_COLUMNS,
        **kwargs,
    )


def run_margin_summary_etl(
    token: str,
    start_date: str | None = None,
    end_date: str | None = None,
    output_path: Path = DEFAULT_SUMMARY_OUTPUT,
    raw_output_path: Path = DEFAULT_RAW_SUMMARY_OUTPUT,
    **kwargs,
) -> dict:
    return run_single_table_etl(
        "fetch_margin_summary",
        token,
        build_summary_fetcher(start_date, end_date),
        convert_tushare_margin_summary,
        output_path=output_path,
        raw_output_path=raw_output_path,
        **kwargs,
    )


def main() -> int:
    args = parse_args()
    if not require_token(args):
        return 2
    control = run_control_kwargs(args)
    exit_code = 0
    try:
        if "summary" in args.tables:
            summary_control = {key: control[key] for key in ("dry_run", "write_log", "backup_root", "create_backup", "max_retries", "retry_interval")}
            result = run_margin_summary_etl(
                token=args.token,
                start_date=args.start_date,
                end_date=args.end_date,
                output_path=args.summary_output,
                raw_output_path=args.raw_summary_output,
                write_raw=args.with_raw,
                **summary_control,
            )
            exit_code = max(exit_code, report_result(result, "fetch_margin_summary"))
        if "detail" in args.tables:
            result = run_margin_etl(
                token=args.token,
                output_root=args.output_root,
                raw_output_root=args.raw_output_root,
                write_raw=args.with_raw,
                start_date=args.start_date,
                end_date=args.end_date,
                **stock_selection_kwargs(args),
                **control,
            )
            exit_code = max(exit_code, report_result(result, "fetch_margin", unit="stocks"))
    except Exception as exc:
        print(f"fetch_margin failed: {exc}", file=sys.stderr)
        return 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
