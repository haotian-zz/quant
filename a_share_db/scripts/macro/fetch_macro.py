#!/usr/bin/env python3
"""Fetch macro and interest-rate reference tables from Tushare.

Outputs:
data/macro/shibor.csv
data/macro/gdp.csv
data/macro/cpi.csv
data/macro/ppi.csv
data/macro/money_supply.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.macro import (
    CPI_COLUMNS,
    DEFAULT_SHIBOR_START_DATE,
    GDP_COLUMNS,
    MONEY_SUPPLY_COLUMNS,
    PPI_COLUMNS,
    SHIBOR_COLUMNS,
    SHIBOR_PAGE_SIZE,
    TUSHARE_CPI_FIELD_MAP,
    TUSHARE_CPI_FIELDS,
    TUSHARE_GDP_FIELD_MAP,
    TUSHARE_GDP_FIELDS,
    TUSHARE_MONEY_SUPPLY_FIELD_MAP,
    TUSHARE_MONEY_SUPPLY_FIELDS,
    TUSHARE_PPI_FIELD_MAP,
    TUSHARE_PPI_FIELDS,
    TUSHARE_SHIBOR_FIELD_MAP,
    TUSHARE_SHIBOR_FIELDS,
)
from a_share_db.constant.paths import CPI_PATH, GDP_PATH, MONEY_SUPPLY_PATH, PPI_PATH, RAW_TUSHARE_ROOT, SHIBOR_PATH
from a_share_db.utils.cli import (
    add_date_range_arguments,
    add_run_control_arguments,
    add_token_argument,
    report_result,
    require_token,
    run_control_kwargs,
)
from a_share_db.utils.etl_common import convert_mapped_frame, fetch_paginated, import_pandas, iter_date_windows
from a_share_db.utils.etl_runners import run_single_table_etl


# Shibor pages are capped at 2000 rows; five-year windows stay under that.
SHIBOR_WINDOW_CALENDAR_DAYS = 365 * 5

# table -> (api, provider fields, field map, local columns, key column, output path)
MACRO_TABLES = {
    "shibor": ("shibor", TUSHARE_SHIBOR_FIELDS, {"date": "rate_date", **TUSHARE_SHIBOR_FIELD_MAP}, SHIBOR_COLUMNS, "rate_date", SHIBOR_PATH),
    "gdp": ("cn_gdp", TUSHARE_GDP_FIELDS, {"quarter": "quarter", **TUSHARE_GDP_FIELD_MAP}, GDP_COLUMNS, "quarter", GDP_PATH),
    "cpi": ("cn_cpi", TUSHARE_CPI_FIELDS, {"month": "month", **TUSHARE_CPI_FIELD_MAP}, CPI_COLUMNS, "month", CPI_PATH),
    "ppi": ("cn_ppi", TUSHARE_PPI_FIELDS, {"month": "month", **TUSHARE_PPI_FIELD_MAP}, PPI_COLUMNS, "month", PPI_PATH),
    "money_supply": ("cn_m", TUSHARE_MONEY_SUPPLY_FIELDS, {"month": "month", **TUSHARE_MONEY_SUPPLY_FIELD_MAP}, MONEY_SUPPLY_COLUMNS, "month", MONEY_SUPPLY_PATH),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Tushare macro tables into data/macro/*.csv.")
    add_token_argument(parser)
    parser.add_argument("--tables", nargs="+", choices=list(MACRO_TABLES), default=list(MACRO_TABLES), help="Tables to fetch. Default: all.")
    add_date_range_arguments(parser, default_start=DEFAULT_SHIBOR_START_DATE, end_defaults_to_today=True)
    parser.add_argument("--with-raw", action="store_true", help="Also write raw provider CSV files under data/raw/tushare/.")
    add_run_control_arguments(parser, resumable=False, loops=False)
    return parser.parse_args()


def build_fetcher(table: str, start_date: str | None, end_date: str | None):
    api_name, fields, _, _, _, _ = MACRO_TABLES[table]

    def fetch(pro):
        if table != "shibor":
            # Monthly and quarterly series are small enough for one paginated query.
            return fetch_paginated(pro, api_name, fields)
        pd = import_pandas()
        frames = [
            fetch_paginated(pro, api_name, fields, page_size=SHIBOR_PAGE_SIZE, start_date=window_start, end_date=window_end)
            for window_start, window_end in iter_date_windows(start_date, end_date, SHIBOR_WINDOW_CALENDAR_DAYS)
        ]
        return pd.concat(frames, ignore_index=True)

    return fetch


def build_converter(table: str):
    _, _, field_map, columns, key_column, _ = MACRO_TABLES[table]

    def convert(raw):
        frame = convert_mapped_frame(
            raw,
            field_map,
            columns,
            sort_columns=[key_column],
            date_columns=["rate_date"],
            code_fields=(),
            code_column=None,
        )
        return frame.drop_duplicates(subset=[key_column], keep="last").reset_index(drop=True)

    return convert


def run_macro_table_etl(table: str, token: str, start_date: str | None = None, end_date: str | None = None, **kwargs) -> dict:
    _, _, _, _, _, output_path = MACRO_TABLES[table]
    return run_single_table_etl(
        f"fetch_macro_{table}",
        token,
        build_fetcher(table, start_date, end_date),
        build_converter(table),
        output_path=output_path,
        raw_output_path=RAW_TUSHARE_ROOT / "macro" / f"{table}.csv",
        **kwargs,
    )


def main() -> int:
    args = parse_args()
    if not require_token(args):
        return 2
    exit_code = 0
    for table in args.tables:
        try:
            result = run_macro_table_etl(
                table,
                token=args.token,
                start_date=args.start_date,
                end_date=args.end_date,
                write_raw=args.with_raw,
                **run_control_kwargs(args),
            )
        except Exception as exc:
            print(f"fetch_macro_{table} failed: {exc}", file=sys.stderr)
            exit_code = 1
            continue
        exit_code = max(exit_code, report_result(result, f"fetch_macro_{table}"))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
