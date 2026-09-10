#!/usr/bin/env python3
"""Fetch financial statements and fundamentals from Tushare by report period.

Outputs (one file per quarterly report period):
data/financial/income/{period}.csv          (income_vip)
data/financial/balance_sheet/{period}.csv   (balancesheet_vip)
data/financial/cash_flow/{period}.csv       (cashflow_vip)
data/financial/indicator/{period}.csv       (fina_indicator_vip)
data/financial/forecast/{period}.csv        (forecast_vip)
data/financial/express/{period}.csv         (express_vip)
data/financial/disclosure_date/{period}.csv (disclosure_date)

Bulk provider interfaces return the whole market for one period, which is
hundreds of times cheaper than one request per stock. Rows keep announce
dates so point-in-time joins can avoid look-ahead bias.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.financial import (
    BALANCE_SHEET_COLUMNS,
    CASH_FLOW_COLUMNS,
    DEFAULT_FINANCIAL_START_DATE,
    DEFAULT_STATEMENT_REPORT_TYPES,
    DISCLOSURE_DATE_COLUMNS,
    DISCLOSURE_DATE_START_DATE,
    EXPRESS_COLUMNS,
    EXPRESS_KEY_COLUMNS,
    FINANCIAL_INDICATOR_COLUMNS,
    FINANCIAL_PAGE_SIZE,
    FORECAST_COLUMNS,
    FORECAST_KEY_COLUMNS,
    INCOME_COLUMNS,
    INDICATOR_KEY_COLUMNS,
    STATEMENT_KEY_COLUMNS,
    TUSHARE_BALANCE_SHEET_FIELD_MAP,
    TUSHARE_BULK_STATEMENT_APIS,
    TUSHARE_CASH_FLOW_FIELD_MAP,
    TUSHARE_COMPANY_TYPE_MAP,
    TUSHARE_DISCLOSURE_DATE_FIELD_MAP,
    TUSHARE_EXPRESS_FIELD_MAP,
    TUSHARE_FINANCIAL_INDICATOR_FIELD_MAP,
    TUSHARE_FORECAST_FIELD_MAP,
    TUSHARE_INCOME_FIELD_MAP,
    TUSHARE_STATEMENT_TYPE_MAP,
)
from a_share_db.constant.paths import (
    BALANCE_SHEET_ROOT,
    CASH_FLOW_ROOT,
    DISCLOSURE_DATE_ROOT,
    EXPRESS_ROOT,
    FINANCIAL_INDICATOR_ROOT,
    FORECAST_ROOT,
    INCOME_ROOT,
    RAW_TUSHARE_ROOT,
)
from a_share_db.utils.cli import (
    add_date_range_arguments,
    add_run_control_arguments,
    add_token_argument,
    report_result,
    require_token,
    run_control_kwargs,
)
from a_share_db.utils.etl_common import (
    convert_mapped_frame,
    fetch_paginated,
    import_pandas,
    iter_report_periods,
)
from a_share_db.utils.etl_runners import run_per_key_etl


STATEMENT_DATE_COLUMNS = ["announce_date", "actual_announce_date", "report_period"]
STATEMENT_VALUE_MAPS = {"report_type": TUSHARE_STATEMENT_TYPE_MAP, "comp_type": TUSHARE_COMPANY_TYPE_MAP}

# table -> (api, field map, local columns, dedupe keys, date columns, value maps, output root, default start)
TABLE_SPECS = {
    "income": (TUSHARE_BULK_STATEMENT_APIS["income"], TUSHARE_INCOME_FIELD_MAP, INCOME_COLUMNS, STATEMENT_KEY_COLUMNS, STATEMENT_DATE_COLUMNS, STATEMENT_VALUE_MAPS, INCOME_ROOT, DEFAULT_FINANCIAL_START_DATE),
    "balance_sheet": (TUSHARE_BULK_STATEMENT_APIS["balance_sheet"], TUSHARE_BALANCE_SHEET_FIELD_MAP, BALANCE_SHEET_COLUMNS, STATEMENT_KEY_COLUMNS, STATEMENT_DATE_COLUMNS, STATEMENT_VALUE_MAPS, BALANCE_SHEET_ROOT, DEFAULT_FINANCIAL_START_DATE),
    "cash_flow": (TUSHARE_BULK_STATEMENT_APIS["cash_flow"], TUSHARE_CASH_FLOW_FIELD_MAP, CASH_FLOW_COLUMNS, STATEMENT_KEY_COLUMNS, STATEMENT_DATE_COLUMNS, STATEMENT_VALUE_MAPS, CASH_FLOW_ROOT, DEFAULT_FINANCIAL_START_DATE),
    "indicator": (TUSHARE_BULK_STATEMENT_APIS["indicator"], TUSHARE_FINANCIAL_INDICATOR_FIELD_MAP, FINANCIAL_INDICATOR_COLUMNS, INDICATOR_KEY_COLUMNS, ["announce_date", "report_period"], {}, FINANCIAL_INDICATOR_ROOT, DEFAULT_FINANCIAL_START_DATE),
    "forecast": (TUSHARE_BULK_STATEMENT_APIS["forecast"], TUSHARE_FORECAST_FIELD_MAP, FORECAST_COLUMNS, FORECAST_KEY_COLUMNS, ["announce_date", "report_period", "first_announce_date"], {}, FORECAST_ROOT, DEFAULT_FINANCIAL_START_DATE),
    "express": (TUSHARE_BULK_STATEMENT_APIS["express"], TUSHARE_EXPRESS_FIELD_MAP, EXPRESS_COLUMNS, EXPRESS_KEY_COLUMNS, ["announce_date", "report_period"], {}, EXPRESS_ROOT, DEFAULT_FINANCIAL_START_DATE),
    "disclosure_date": ("disclosure_date", TUSHARE_DISCLOSURE_DATE_FIELD_MAP, DISCLOSURE_DATE_COLUMNS, ["code", "report_period"], ["announce_date", "report_period", "planned_date", "actual_date"], {}, DISCLOSURE_DATE_ROOT, DISCLOSURE_DATE_START_DATE),
}
STATEMENT_TABLES = {"income", "balance_sheet", "cash_flow"}
DEFAULT_REFRESH_RECENT_DAYS = 400


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Tushare financial statements by report period into data/financial/{table}/{period}.csv."
    )
    add_token_argument(parser)
    parser.add_argument("--tables", nargs="+", choices=list(TABLE_SPECS), default=list(TABLE_SPECS), help="Tables to fetch. Default: all.")
    parser.add_argument("--periods", nargs="+", help="Explicit report periods in YYYYMMDD format, for example 20231231.")
    add_date_range_arguments(parser, default_start=None, end_defaults_to_today=True)
    parser.add_argument(
        "--report-types",
        nargs="+",
        default=DEFAULT_STATEMENT_REPORT_TYPES,
        help="Provider report_type codes for income/balance_sheet/cash_flow. Default: 1 (consolidated).",
    )
    parser.add_argument(
        "--refresh-recent-days",
        type=int,
        default=DEFAULT_REFRESH_RECENT_DAYS,
        help=f"With --resume, periods ending within this many days are always re-fetched. Default: {DEFAULT_REFRESH_RECENT_DAYS}.",
    )
    parser.add_argument("--with-raw", action="store_true", help="Also write raw provider CSV files under data/raw/tushare/.")
    add_run_control_arguments(parser)
    return parser.parse_args()


def build_fetcher(api_name: str, fields: list[str], report_types: list[str], request_interval: float, is_statement: bool, is_disclosure: bool):
    def fetch_period(pro, period: str):
        pd = import_pandas()
        if is_disclosure:
            return fetch_paginated(pro, api_name, fields, page_size=FINANCIAL_PAGE_SIZE, request_interval=request_interval, end_date=period)
        if not is_statement:
            return fetch_paginated(pro, api_name, fields, page_size=FINANCIAL_PAGE_SIZE, request_interval=request_interval, period=period)
        # Statement interfaces accept one report_type per request.
        frames = [
            fetch_paginated(pro, api_name, fields, page_size=FINANCIAL_PAGE_SIZE, request_interval=request_interval, period=period, report_type=report_type)
            for report_type in report_types
        ]
        return pd.concat(frames, ignore_index=True)

    return fetch_period


def build_converter(field_map: dict, columns: list[str], keys: list[str], date_columns: list[str], value_maps: dict):
    def convert(raw, period: str | None = None):
        frame = convert_mapped_frame(
            raw,
            field_map,
            columns,
            sort_columns=keys,
            date_columns=date_columns,
            value_maps=value_maps,
        )
        if "is_update" in frame.columns:
            # The provider repeats rows; keep the flagged update when both exist.
            frame = frame.sort_values(keys + ["is_update"], kind="stable")
        return frame.drop_duplicates(subset=keys, keep="last").reset_index(drop=True)

    return convert


def build_resume_rule(refresh_recent_days: int):
    cutoff = (datetime.now() - timedelta(days=refresh_recent_days)).strftime("%Y%m%d")

    def should_skip(period: str, path: Path) -> bool:
        # Old periods are stable; recent ones still receive filings and restatements.
        return period < cutoff and path.exists() and path.stat().st_size > 0

    return should_skip


def run_financial_table_etl(
    table: str,
    token: str,
    periods=None,
    start_date: str | None = None,
    end_date: str | None = None,
    report_types=DEFAULT_STATEMENT_REPORT_TYPES,
    refresh_recent_days: int = DEFAULT_REFRESH_RECENT_DAYS,
    **kwargs,
) -> dict:
    api_name, field_map, columns, keys, date_columns, value_maps, output_root, default_start = TABLE_SPECS[table]
    selected_periods = list(periods) if periods else iter_report_periods(start_date or default_start, end_date)
    return run_per_key_etl(
        f"fetch_{table}",
        token,
        keys=selected_periods,
        fetch_fn=build_fetcher(
            api_name,
            list(field_map.keys()),
            list(report_types),
            kwargs.get("request_interval", 0.0),
            is_statement=table in STATEMENT_TABLES,
            is_disclosure=table == "disclosure_date",
        ),
        convert_fn=build_converter(field_map, columns, keys, date_columns, value_maps),
        output_path_fn=lambda period: Path(output_root) / f"{period}.csv",
        raw_output_path_fn=lambda period: RAW_TUSHARE_ROOT / "financial" / table / f"{period}.csv",
        resume_skip_fn=build_resume_rule(refresh_recent_days),
        **kwargs,
    )


def main() -> int:
    args = parse_args()
    if not require_token(args):
        return 2
    exit_code = 0
    for table in args.tables:
        try:
            result = run_financial_table_etl(
                table,
                token=args.token,
                periods=args.periods,
                start_date=args.start_date,
                end_date=args.end_date,
                report_types=args.report_types,
                refresh_recent_days=args.refresh_recent_days,
                write_raw=args.with_raw,
                **run_control_kwargs(args),
            )
        except Exception as exc:
            print(f"fetch_{table} failed: {exc}", file=sys.stderr)
            exit_code = 1
            continue
        exit_code = max(exit_code, report_result(result, f"fetch_{table}", unit="periods"))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
