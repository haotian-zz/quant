#!/usr/bin/env python3
"""Fetch per-stock order-size money flow from Tushare.

Outputs:
data/market_data/moneyflow/{code}.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.moneyflow import (
    DEFAULT_MONEYFLOW_START_DATE,
    MONEYFLOW_COLUMNS,
    MONEYFLOW_PAGE_SIZE,
    TUSHARE_MONEYFLOW_AMOUNT_TO_LOCAL,
    TUSHARE_MONEYFLOW_FIELD_MAP,
    TUSHARE_MONEYFLOW_FIELDS,
    TUSHARE_MONEYFLOW_VOLUME_TO_LOCAL,
)
from a_share_db.constant.paths import MONEYFLOW_ROOT, RAW_TUSHARE_ROOT
from a_share_db.utils.cli import (
    add_date_range_arguments,
    add_output_arguments,
    add_run_control_arguments,
    add_stock_selection_arguments,
    add_token_argument,
    require_token,
    run_control_kwargs,
    run_main,
    stock_selection_kwargs,
)
from a_share_db.utils.etl_common import convert_mapped_frame, fetch_paginated
from a_share_db.utils.etl_runners import run_per_stock_etl


DEFAULT_OUTPUT_ROOT = MONEYFLOW_ROOT
DEFAULT_RAW_OUTPUT_ROOT = RAW_TUSHARE_ROOT / "moneyflow"
FIELD_MAP = {"ts_code": "code", "trade_date": "trade_date", **TUSHARE_MONEYFLOW_FIELD_MAP}
# Provider volumes are in 手 and amounts in 万元.
SCALES = {
    field: (TUSHARE_MONEYFLOW_VOLUME_TO_LOCAL if field.endswith("_vol") else TUSHARE_MONEYFLOW_AMOUNT_TO_LOCAL)
    for field in TUSHARE_MONEYFLOW_FIELD_MAP
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Tushare moneyflow data and build data/market_data/moneyflow/{code}.csv."
    )
    add_token_argument(parser)
    add_stock_selection_arguments(parser)
    add_date_range_arguments(parser, default_start=DEFAULT_MONEYFLOW_START_DATE, end_defaults_to_today=True)
    add_output_arguments(parser, DEFAULT_OUTPUT_ROOT, DEFAULT_RAW_OUTPUT_ROOT)
    add_run_control_arguments(parser)
    return parser.parse_args()


def fetch_moneyflow(pro, ts_code: str, stock: dict, start_date: str | None, end_date: str | None):
    return fetch_paginated(
        pro,
        "moneyflow",
        TUSHARE_MONEYFLOW_FIELDS,
        page_size=MONEYFLOW_PAGE_SIZE,
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
    )


def convert_tushare_moneyflow(raw, stock: dict | None = None):
    """Convert raw Tushare moneyflow rows into the local moneyflow schema."""
    return convert_mapped_frame(
        raw,
        FIELD_MAP,
        MONEYFLOW_COLUMNS,
        sort_columns=["code", "trade_date"],
        date_columns=["trade_date"],
        scales=SCALES,
    )


def run_moneyflow_etl(token: str, output_root: Path = DEFAULT_OUTPUT_ROOT, raw_output_root: Path = DEFAULT_RAW_OUTPUT_ROOT, **kwargs) -> dict:
    return run_per_stock_etl(
        "fetch_moneyflow",
        token,
        fetch_moneyflow,
        convert_tushare_moneyflow,
        output_root=output_root,
        raw_output_root=raw_output_root,
        **kwargs,
    )


def main() -> int:
    args = parse_args()
    if not require_token(args):
        return 2
    return run_main(
        "fetch_moneyflow",
        lambda: run_moneyflow_etl(
            token=args.token,
            output_root=args.output_root,
            raw_output_root=args.raw_output_root,
            write_raw=args.with_raw,
            start_date=args.start_date,
            end_date=args.end_date,
            **stock_selection_kwargs(args),
            **run_control_kwargs(args),
        ),
        unit="stocks",
    )


if __name__ == "__main__":
    raise SystemExit(main())
