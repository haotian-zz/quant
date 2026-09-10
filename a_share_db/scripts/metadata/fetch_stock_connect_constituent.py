#!/usr/bin/env python3
"""Fetch Shanghai/Shenzhen-Hong Kong Stock Connect constituent history from Tushare.

Outputs:
data/metadata/stock_connect_constituent.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.paths import RAW_TUSHARE_ROOT, STOCK_CONNECT_CONSTITUENT_PATH
from a_share_db.constant.stock_connect import (
    STOCK_CONNECT_CONSTITUENT_COLUMNS,
    STOCK_CONNECT_QUERY_IS_NEW,
    STOCK_CONNECT_QUERY_TYPES,
    TUSHARE_HS_TYPE_MAP,
    TUSHARE_STOCK_CONNECT_CONST_FIELDS,
)
from a_share_db.utils.cli import (
    add_output_arguments,
    add_run_control_arguments,
    add_token_argument,
    require_token,
    run_control_kwargs,
    run_main,
)
from a_share_db.utils.etl_common import convert_mapped_frame, fetch_paginated, import_pandas
from a_share_db.utils.etl_runners import run_single_table_etl


DEFAULT_OUTPUT = STOCK_CONNECT_CONSTITUENT_PATH
DEFAULT_RAW_OUTPUT = RAW_TUSHARE_ROOT / "stock_connect_constituent.csv"
FIELD_MAP = dict(zip(TUSHARE_STOCK_CONNECT_CONST_FIELDS, STOCK_CONNECT_CONSTITUENT_COLUMNS))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Tushare hs_const data and build data/metadata/stock_connect_constituent.csv."
    )
    add_token_argument(parser)
    add_output_arguments(parser, DEFAULT_OUTPUT, DEFAULT_RAW_OUTPUT, output_is_dir=False)
    parser.add_argument("--limit", type=int, help="Write only the first N normalized rows. Useful for smoke tests.")
    add_run_control_arguments(parser, resumable=False, loops=False)
    return parser.parse_args()


def fetch_stock_connect_constituent(pro):
    pd = import_pandas()
    # Current and historical members come from separate provider queries.
    frames = [
        fetch_paginated(pro, "hs_const", TUSHARE_STOCK_CONNECT_CONST_FIELDS, hs_type=hs_type, is_new=is_new)
        for hs_type in STOCK_CONNECT_QUERY_TYPES
        for is_new in STOCK_CONNECT_QUERY_IS_NEW
    ]
    return pd.concat(frames, ignore_index=True).drop_duplicates(subset=["ts_code", "hs_type", "in_date"], keep="last")


def convert_tushare_stock_connect_constituent(raw):
    """Convert raw Tushare hs_const rows into the local stock_connect_constituent schema."""
    return convert_mapped_frame(
        raw,
        FIELD_MAP,
        STOCK_CONNECT_CONSTITUENT_COLUMNS,
        sort_columns=["code", "connect_market", "in_date"],
        date_columns=["in_date", "out_date"],
        value_maps={"hs_type": TUSHARE_HS_TYPE_MAP},
    )


def run_stock_connect_constituent_etl(token: str, output_path: Path = DEFAULT_OUTPUT, raw_output_path: Path = DEFAULT_RAW_OUTPUT, **kwargs) -> dict:
    return run_single_table_etl(
        "fetch_stock_connect_constituent",
        token,
        fetch_stock_connect_constituent,
        convert_tushare_stock_connect_constituent,
        output_path=output_path,
        raw_output_path=raw_output_path,
        **kwargs,
    )


def main() -> int:
    args = parse_args()
    if not require_token(args):
        return 2
    return run_main(
        "fetch_stock_connect_constituent",
        lambda: run_stock_connect_constituent_etl(
            token=args.token,
            output_path=args.output,
            raw_output_path=args.raw_output,
            write_raw=args.with_raw,
            limit=args.limit,
            **run_control_kwargs(args),
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())
