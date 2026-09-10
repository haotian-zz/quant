#!/usr/bin/env python3
"""Fetch index metadata from Tushare.

Outputs:
data/metadata/index_basic.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.index import (
    INDEX_BASIC_COLUMNS,
    INDEX_BASIC_MARKETS,
    INDEX_BASIC_PAGE_SIZE,
    TUSHARE_INDEX_BASIC_FIELDS,
)
from a_share_db.constant.paths import INDEX_BASIC_PATH, RAW_TUSHARE_ROOT
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


DEFAULT_OUTPUT = INDEX_BASIC_PATH
DEFAULT_RAW_OUTPUT = RAW_TUSHARE_ROOT / "index_basic.csv"
FIELD_MAP = dict(zip(TUSHARE_INDEX_BASIC_FIELDS, INDEX_BASIC_COLUMNS))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Tushare index_basic data and build data/metadata/index_basic.csv.")
    add_token_argument(parser)
    parser.add_argument("--markets", nargs="+", default=INDEX_BASIC_MARKETS, help=f"Index markets to query. Default: {' '.join(INDEX_BASIC_MARKETS)}.")
    add_output_arguments(parser, DEFAULT_OUTPUT, DEFAULT_RAW_OUTPUT, output_is_dir=False)
    parser.add_argument("--limit", type=int, help="Write only the first N normalized rows. Useful for smoke tests.")
    add_run_control_arguments(parser, resumable=False, loops=False)
    return parser.parse_args()


def build_fetcher(markets):
    def fetch_index_basic(pro):
        pd = import_pandas()
        frames = [
            fetch_paginated(pro, "index_basic", TUSHARE_INDEX_BASIC_FIELDS, page_size=INDEX_BASIC_PAGE_SIZE, market=market)
            for market in markets
        ]
        return pd.concat(frames, ignore_index=True).drop_duplicates(subset=["ts_code"], keep="last")

    return fetch_index_basic


def convert_tushare_index_basic(raw):
    """Convert raw Tushare index_basic rows into the local index_basic schema."""
    # Index identifiers keep their market suffix (see constant/index.py).
    return convert_mapped_frame(
        raw,
        FIELD_MAP,
        INDEX_BASIC_COLUMNS,
        sort_columns=["market", "index_code"],
        date_columns=["base_date", "list_date", "expire_date"],
        code_fields=(),
        code_column=None,
    )


def run_index_basic_etl(token: str, markets=INDEX_BASIC_MARKETS, output_path: Path = DEFAULT_OUTPUT, raw_output_path: Path = DEFAULT_RAW_OUTPUT, **kwargs) -> dict:
    return run_single_table_etl(
        "fetch_index_basic",
        token,
        build_fetcher(markets),
        convert_tushare_index_basic,
        output_path=output_path,
        raw_output_path=raw_output_path,
        **kwargs,
    )


def main() -> int:
    args = parse_args()
    if not require_token(args):
        return 2
    return run_main(
        "fetch_index_basic",
        lambda: run_index_basic_etl(
            token=args.token,
            markets=args.markets,
            output_path=args.output,
            raw_output_path=args.raw_output,
            write_raw=args.with_raw,
            limit=args.limit,
            **run_control_kwargs(args),
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())
