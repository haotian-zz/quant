#!/usr/bin/env python3
"""Fetch index constituent weights from Tushare.

Outputs:
data/market_data/index_weight/{index_code}.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.index import (
    DEFAULT_INDEX_WEIGHT_CODES,
    DEFAULT_INDEX_WEIGHT_START_DATE,
    INDEX_WEIGHT_COLUMNS,
    INDEX_WEIGHT_PAGE_SIZE,
    INDEX_WEIGHT_WINDOW_CALENDAR_DAYS,
    TUSHARE_INDEX_WEIGHT_FIELDS,
)
from a_share_db.constant.paths import INDEX_WEIGHT_ROOT, RAW_TUSHARE_ROOT
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
from a_share_db.utils.etl_runners import run_per_key_etl


DEFAULT_OUTPUT_ROOT = INDEX_WEIGHT_ROOT
DEFAULT_RAW_OUTPUT_ROOT = RAW_TUSHARE_ROOT / "index_weight"
FIELD_MAP = dict(zip(TUSHARE_INDEX_WEIGHT_FIELDS, INDEX_WEIGHT_COLUMNS))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Tushare index_weight data and build data/market_data/index_weight/{index_code}.csv."
    )
    add_token_argument(parser)
    parser.add_argument("--index-codes", nargs="+", default=DEFAULT_INDEX_WEIGHT_CODES, help="Index codes such as 000300.SH. Default: project universe list.")
    add_date_range_arguments(parser, default_start=DEFAULT_INDEX_WEIGHT_START_DATE, end_defaults_to_today=True)
    add_output_arguments(parser, DEFAULT_OUTPUT_ROOT, DEFAULT_RAW_OUTPUT_ROOT)
    add_run_control_arguments(parser)
    return parser.parse_args()


def build_fetcher(start_date: str | None, end_date: str | None, request_interval: float):
    def fetch_index_weight(pro, index_code: str):
        pd = import_pandas()
        # Yearly windows plus pagination keep wide indices (1000+ members) safe.
        frames = [
            fetch_paginated(
                pro,
                "index_weight",
                TUSHARE_INDEX_WEIGHT_FIELDS,
                page_size=INDEX_WEIGHT_PAGE_SIZE,
                request_interval=request_interval,
                index_code=index_code,
                start_date=window_start,
                end_date=window_end,
            )
            for window_start, window_end in iter_date_windows(start_date, end_date, INDEX_WEIGHT_WINDOW_CALENDAR_DAYS)
        ]
        frame = pd.concat(frames, ignore_index=True)
        return frame.drop_duplicates(subset=["index_code", "con_code", "trade_date"], keep="last")

    return fetch_index_weight


def convert_tushare_index_weight(raw, index_code: str | None = None):
    """Convert raw Tushare index_weight rows into the local index_weight schema."""
    return convert_mapped_frame(
        raw,
        FIELD_MAP,
        INDEX_WEIGHT_COLUMNS,
        sort_columns=["index_code", "trade_date", "code"],
        date_columns=["trade_date"],
        code_fields=("con_code",),
    )


def run_index_weight_etl(
    token: str,
    index_codes=DEFAULT_INDEX_WEIGHT_CODES,
    start_date: str | None = None,
    end_date: str | None = None,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    raw_output_root: Path = DEFAULT_RAW_OUTPUT_ROOT,
    **kwargs,
) -> dict:
    return run_per_key_etl(
        "fetch_index_weight",
        token,
        keys=list(index_codes),
        fetch_fn=build_fetcher(start_date, end_date, kwargs.get("request_interval", 0.0)),
        convert_fn=convert_tushare_index_weight,
        output_path_fn=lambda index_code: Path(output_root) / f"{index_code}.csv",
        raw_output_path_fn=lambda index_code: Path(raw_output_root) / f"{index_code}.csv",
        **kwargs,
    )


def main() -> int:
    args = parse_args()
    if not require_token(args):
        return 2
    return run_main(
        "fetch_index_weight",
        lambda: run_index_weight_etl(
            token=args.token,
            index_codes=args.index_codes,
            start_date=args.start_date,
            end_date=args.end_date,
            output_root=args.output_root,
            raw_output_root=args.raw_output_root,
            write_raw=args.with_raw,
            **run_control_kwargs(args),
        ),
        unit="indices",
    )


if __name__ == "__main__":
    raise SystemExit(main())
