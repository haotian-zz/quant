#!/usr/bin/env python3
"""Fetch daily market event tables from Tushare by trade date.

Outputs:
data/market_data/dragon_tiger_list/{year}.csv   (top_list)
data/market_data/dragon_tiger_inst/{year}.csv   (top_inst)
data/market_data/block_trade/{year}.csv         (block_trade)
data/market_data/limit_list/{year}.csv          (limit_list_d)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.events import (
    BLOCK_TRADE_COLUMNS,
    DEFAULT_BLOCK_TRADE_START_DATE,
    DEFAULT_DRAGON_TIGER_START_DATE,
    DEFAULT_LIMIT_LIST_START_DATE,
    DRAGON_TIGER_INST_COLUMNS,
    DRAGON_TIGER_LIST_COLUMNS,
    LIMIT_LIST_COLUMNS,
    TUSHARE_BLOCK_TRADE_AMOUNT_TO_LOCAL,
    TUSHARE_BLOCK_TRADE_FIELD_MAP,
    TUSHARE_BLOCK_TRADE_FIELDS,
    TUSHARE_BLOCK_TRADE_VOLUME_TO_LOCAL,
    TUSHARE_LIMIT_LIST_FIELD_MAP,
    TUSHARE_LIMIT_LIST_FIELDS,
    TUSHARE_LIMIT_TYPE_MAP,
    TUSHARE_TOP_INST_FIELD_MAP,
    TUSHARE_TOP_INST_FIELDS,
    TUSHARE_TOP_LIST_FIELD_MAP,
    TUSHARE_TOP_LIST_FIELDS,
)
from a_share_db.constant.paths import (
    BLOCK_TRADE_ROOT,
    DRAGON_TIGER_INST_ROOT,
    DRAGON_TIGER_LIST_ROOT,
    LIMIT_LIST_ROOT,
    RAW_TUSHARE_ROOT,
)
from a_share_db.utils.cli import (
    add_calendar_arguments,
    add_date_range_arguments,
    add_run_control_arguments,
    add_token_argument,
    report_result,
    require_token,
    run_control_kwargs,
)
from a_share_db.utils.etl_common import convert_mapped_frame, fetch_paginated
from a_share_db.utils.etl_runners import run_per_date_etl


def convert_dragon_tiger_list(raw):
    return convert_mapped_frame(raw, TUSHARE_TOP_LIST_FIELD_MAP, DRAGON_TIGER_LIST_COLUMNS, ["trade_date", "code"], date_columns=["trade_date"])


def convert_dragon_tiger_inst(raw):
    return convert_mapped_frame(raw, TUSHARE_TOP_INST_FIELD_MAP, DRAGON_TIGER_INST_COLUMNS, ["trade_date", "code", "seat_name"], date_columns=["trade_date"])


def convert_block_trade(raw):
    return convert_mapped_frame(
        raw,
        TUSHARE_BLOCK_TRADE_FIELD_MAP,
        BLOCK_TRADE_COLUMNS,
        ["trade_date", "code"],
        date_columns=["trade_date"],
        scales={"vol": TUSHARE_BLOCK_TRADE_VOLUME_TO_LOCAL, "amount": TUSHARE_BLOCK_TRADE_AMOUNT_TO_LOCAL},
    )


def convert_limit_list(raw):
    return convert_mapped_frame(
        raw,
        TUSHARE_LIMIT_LIST_FIELD_MAP,
        LIMIT_LIST_COLUMNS,
        ["trade_date", "code"],
        date_columns=["trade_date"],
        value_maps={"limit": TUSHARE_LIMIT_TYPE_MAP},
    )


# Each event table: provider api, provider fields, converter, output root, default start.
EVENT_TABLES = {
    "dragon_tiger_list": ("top_list", TUSHARE_TOP_LIST_FIELDS, convert_dragon_tiger_list, DRAGON_TIGER_LIST_ROOT, DEFAULT_DRAGON_TIGER_START_DATE),
    "dragon_tiger_inst": ("top_inst", TUSHARE_TOP_INST_FIELDS, convert_dragon_tiger_inst, DRAGON_TIGER_INST_ROOT, DEFAULT_DRAGON_TIGER_START_DATE),
    "block_trade": ("block_trade", TUSHARE_BLOCK_TRADE_FIELDS, convert_block_trade, BLOCK_TRADE_ROOT, DEFAULT_BLOCK_TRADE_START_DATE),
    "limit_list": ("limit_list_d", TUSHARE_LIMIT_LIST_FIELDS, convert_limit_list, LIMIT_LIST_ROOT, DEFAULT_LIMIT_LIST_START_DATE),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Tushare daily event tables (top_list, top_inst, block_trade, limit_list_d) by trade date."
    )
    add_token_argument(parser)
    parser.add_argument("--tables", nargs="+", choices=list(EVENT_TABLES), default=list(EVENT_TABLES), help="Event tables to fetch. Default: all.")
    add_date_range_arguments(parser, default_start=None, end_defaults_to_today=True)
    add_calendar_arguments(parser)
    parser.add_argument("--with-raw", action="store_true", help="Also write raw provider CSV files under data/raw/tushare/.")
    add_run_control_arguments(parser)
    return parser.parse_args()


def run_market_event_etl(table: str, token: str, start_date: str | None = None, end_date: str | None = None, **kwargs) -> dict:
    api_name, fields, convert_fn, output_root, default_start = EVENT_TABLES[table]

    def fetch_fn(pro, trade_date: str):
        return fetch_paginated(pro, api_name, fields, trade_date=trade_date)

    return run_per_date_etl(
        f"fetch_{table}",
        token,
        fetch_fn,
        convert_fn,
        output_root=output_root,
        raw_output_root=RAW_TUSHARE_ROOT / table,
        # Each table has its own provider coverage start when the caller passes none.
        start_date=start_date or default_start,
        end_date=end_date,
        **kwargs,
    )


def main() -> int:
    args = parse_args()
    if not require_token(args):
        return 2
    exit_code = 0
    for table in args.tables:
        try:
            result = run_market_event_etl(
                table,
                token=args.token,
                start_date=args.start_date,
                end_date=args.end_date,
                trade_calendar_path=args.trade_calendar,
                limit_days=args.limit_days,
                write_raw=args.with_raw,
                **run_control_kwargs(args),
            )
        except Exception as exc:
            print(f"fetch_{table} failed: {exc}", file=sys.stderr)
            exit_code = 1
            continue
        exit_code = max(exit_code, report_result(result, f"fetch_{table}", unit="trading days"))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
