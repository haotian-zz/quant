#!/usr/bin/env python3
"""Fetch listed company profiles from Tushare.

Outputs:
data/metadata/stock_company.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.paths import RAW_TUSHARE_ROOT, STOCK_COMPANY_PATH
from a_share_db.constant.stock_company import (
    STOCK_COMPANY_COLUMNS,
    STOCK_COMPANY_EXCHANGES,
    TUSHARE_REGISTERED_CAPITAL_TO_LOCAL,
    TUSHARE_STOCK_COMPANY_FIELD_MAP,
    TUSHARE_STOCK_COMPANY_FIELDS,
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


DEFAULT_OUTPUT = STOCK_COMPANY_PATH
DEFAULT_RAW_OUTPUT = RAW_TUSHARE_ROOT / "stock_company.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Tushare stock_company data and build data/metadata/stock_company.csv."
    )
    add_token_argument(parser)
    parser.add_argument("--exchanges", nargs="+", default=STOCK_COMPANY_EXCHANGES, help="Exchanges to query. Default: SSE SZSE BSE.")
    add_output_arguments(parser, DEFAULT_OUTPUT, DEFAULT_RAW_OUTPUT, output_is_dir=False)
    parser.add_argument("--limit", type=int, help="Write only the first N normalized rows. Useful for smoke tests.")
    add_run_control_arguments(parser, resumable=False, loops=False)
    return parser.parse_args()


def build_fetcher(exchanges):
    def fetch_stock_company(pro):
        pd = import_pandas()
        # The provider requires one request per exchange.
        frames = [
            fetch_paginated(pro, "stock_company", TUSHARE_STOCK_COMPANY_FIELDS, exchange=exchange.strip().upper())
            for exchange in exchanges
        ]
        return pd.concat(frames, ignore_index=True).drop_duplicates(subset=["ts_code"], keep="last")

    return fetch_stock_company


def convert_tushare_stock_company(raw):
    """Convert raw Tushare stock_company rows into the local stock_company schema."""
    return convert_mapped_frame(
        raw,
        TUSHARE_STOCK_COMPANY_FIELD_MAP,
        STOCK_COMPANY_COLUMNS,
        sort_columns=["exchange", "code"],
        date_columns=["setup_date"],
        scales={"reg_capital": TUSHARE_REGISTERED_CAPITAL_TO_LOCAL},
    )


def run_stock_company_etl(token: str, exchanges=STOCK_COMPANY_EXCHANGES, output_path: Path = DEFAULT_OUTPUT, raw_output_path: Path = DEFAULT_RAW_OUTPUT, **kwargs) -> dict:
    return run_single_table_etl(
        "fetch_stock_company",
        token,
        build_fetcher(exchanges),
        convert_tushare_stock_company,
        output_path=output_path,
        raw_output_path=raw_output_path,
        **kwargs,
    )


def main() -> int:
    args = parse_args()
    if not require_token(args):
        return 2
    return run_main(
        "fetch_stock_company",
        lambda: run_stock_company_etl(
            token=args.token,
            exchanges=args.exchanges,
            output_path=args.output,
            raw_output_path=args.raw_output,
            write_raw=args.with_raw,
            limit=args.limit,
            **run_control_kwargs(args),
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())
