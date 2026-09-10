#!/usr/bin/env python3
"""Fetch aggregate northbound/southbound Stock Connect flows from Tushare.

Outputs:
data/market_data/stock_connect_flow.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.paths import RAW_TUSHARE_ROOT, STOCK_CONNECT_FLOW_PATH
from a_share_db.constant.stock_connect import (
    DEFAULT_STOCK_CONNECT_FLOW_START_DATE,
    STOCK_CONNECT_FLOW_COLUMNS,
    STOCK_CONNECT_FLOW_PAGE_SIZE,
    TUSHARE_STOCK_CONNECT_FLOW_FIELDS,
    TUSHARE_STOCK_CONNECT_FLOW_TO_LOCAL,
)
from a_share_db.utils.cli import (
    add_date_range_arguments,
    add_output_arguments,
    add_run_control_arguments,
    add_token_argument,
    require_token,
    run_control_kwargs,
    run_main,
)
from a_share_db.utils.etl_common import convert_mapped_frame, fetch_paginated, import_pandas, iter_date_windows
from a_share_db.utils.etl_runners import run_single_table_etl


DEFAULT_OUTPUT = STOCK_CONNECT_FLOW_PATH
DEFAULT_RAW_OUTPUT = RAW_TUSHARE_ROOT / "stock_connect_flow.csv"
FIELD_MAP = dict(zip(TUSHARE_STOCK_CONNECT_FLOW_FIELDS, STOCK_CONNECT_FLOW_COLUMNS))
SCALES = {field: TUSHARE_STOCK_CONNECT_FLOW_TO_LOCAL for field in TUSHARE_STOCK_CONNECT_FLOW_FIELDS if field != "trade_date"}
# The provider caps this interface at 300 rows, so history is fetched by year.
WINDOW_CALENDAR_DAYS = 300


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Tushare moneyflow_hsgt data and build data/market_data/stock_connect_flow.csv."
    )
    add_token_argument(parser)
    add_date_range_arguments(parser, default_start=DEFAULT_STOCK_CONNECT_FLOW_START_DATE, end_defaults_to_today=True)
    add_output_arguments(parser, DEFAULT_OUTPUT, DEFAULT_RAW_OUTPUT, output_is_dir=False)
    add_run_control_arguments(parser, resumable=False, loops=False)
    return parser.parse_args()


def build_fetcher(start_date: str | None, end_date: str | None):
    def fetch_stock_connect_flow(pro):
        pd = import_pandas()
        frames = [
            fetch_paginated(
                pro,
                "moneyflow_hsgt",
                TUSHARE_STOCK_CONNECT_FLOW_FIELDS,
                page_size=STOCK_CONNECT_FLOW_PAGE_SIZE,
                start_date=window_start,
                end_date=window_end,
            )
            for window_start, window_end in iter_date_windows(start_date, end_date, WINDOW_CALENDAR_DAYS)
        ]
        return pd.concat(frames, ignore_index=True).drop_duplicates(subset=["trade_date"], keep="last")

    return fetch_stock_connect_flow


def convert_tushare_stock_connect_flow(raw):
    """Convert raw Tushare moneyflow_hsgt rows into the local stock_connect_flow schema."""
    return convert_mapped_frame(
        raw,
        FIELD_MAP,
        STOCK_CONNECT_FLOW_COLUMNS,
        sort_columns=["trade_date"],
        date_columns=["trade_date"],
        scales=SCALES,
        code_fields=(),
        code_column=None,
    )


def run_stock_connect_flow_etl(token: str, start_date: str | None = None, end_date: str | None = None, output_path: Path = DEFAULT_OUTPUT, raw_output_path: Path = DEFAULT_RAW_OUTPUT, **kwargs) -> dict:
    # The provider rejects unbounded queries, so importers get the coverage start too.
    start_date = start_date or DEFAULT_STOCK_CONNECT_FLOW_START_DATE
    return run_single_table_etl(
        "fetch_stock_connect_flow",
        token,
        build_fetcher(start_date, end_date),
        convert_tushare_stock_connect_flow,
        output_path=output_path,
        raw_output_path=raw_output_path,
        **kwargs,
    )


def main() -> int:
    args = parse_args()
    if not require_token(args):
        return 2
    return run_main(
        "fetch_stock_connect_flow",
        lambda: run_stock_connect_flow_etl(
            token=args.token,
            start_date=args.start_date,
            end_date=args.end_date,
            output_path=args.output,
            raw_output_path=args.raw_output,
            write_raw=args.with_raw,
            **run_control_kwargs(args),
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())
