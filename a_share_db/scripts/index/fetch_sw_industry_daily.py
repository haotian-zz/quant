#!/usr/bin/env python3
"""Fetch Shenwan industry index daily quotes from Tushare.

Outputs:
data/market_data/sw_industry_daily/{industry_index_code}.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.industry import (
    DEFAULT_SW_DAILY_START_DATE,
    SW_DAILY_PAGE_SIZE,
    SW_INDUSTRY_DAILY_COLUMNS,
    SW_LEVELS,
    TUSHARE_SW_AMOUNT_TO_LOCAL,
    TUSHARE_SW_DAILY_FIELDS,
    TUSHARE_SW_MARKET_VALUE_TO_LOCAL,
    TUSHARE_SW_VOLUME_TO_LOCAL,
)
from a_share_db.constant.paths import RAW_TUSHARE_ROOT, SW_INDUSTRY_DAILY_ROOT, SW_INDUSTRY_PATH
from a_share_db.utils.cli import (
    add_date_range_arguments,
    add_output_arguments,
    add_run_control_arguments,
    add_token_argument,
    require_token,
    run_control_kwargs,
    run_main,
)
from a_share_db.utils.etl_common import convert_mapped_frame, fetch_paginated, import_pandas
from a_share_db.utils.etl_runners import run_per_key_etl


DEFAULT_OUTPUT_ROOT = SW_INDUSTRY_DAILY_ROOT
DEFAULT_RAW_OUTPUT_ROOT = RAW_TUSHARE_ROOT / "sw_industry_daily"
FIELD_MAP = dict(zip(TUSHARE_SW_DAILY_FIELDS, SW_INDUSTRY_DAILY_COLUMNS))
SCALES = {
    "vol": TUSHARE_SW_VOLUME_TO_LOCAL,
    "amount": TUSHARE_SW_AMOUNT_TO_LOCAL,
    "float_mv": TUSHARE_SW_MARKET_VALUE_TO_LOCAL,
    "total_mv": TUSHARE_SW_MARKET_VALUE_TO_LOCAL,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Tushare sw_daily data and build data/market_data/sw_industry_daily/{industry_index_code}.csv."
    )
    add_token_argument(parser)
    parser.add_argument("--index-codes", nargs="+", help="Industry index codes such as 801010.SI. Default: every code in sw_industry.csv.")
    parser.add_argument("--levels", nargs="+", choices=SW_LEVELS, default=SW_LEVELS, help="Classification levels to include when reading sw_industry.csv. Default: L1 L2 L3.")
    parser.add_argument("--classification", type=Path, default=SW_INDUSTRY_PATH, help=f"Local sw_industry.csv path. Default: {SW_INDUSTRY_PATH}")
    add_date_range_arguments(parser, default_start=DEFAULT_SW_DAILY_START_DATE, end_defaults_to_today=True)
    add_output_arguments(parser, DEFAULT_OUTPUT_ROOT, DEFAULT_RAW_OUTPUT_ROOT)
    add_run_control_arguments(parser)
    return parser.parse_args()


def load_industry_codes(classification_path: Path, levels) -> list[str]:
    pd = import_pandas()
    classification_path = Path(classification_path)
    if not classification_path.exists():
        raise FileNotFoundError(f"Missing classification file, fetch it first: {classification_path}")
    frame = pd.read_csv(classification_path, dtype=str).fillna("")
    frame = frame[frame["level"].isin(list(levels))]
    return sorted(frame["industry_index_code"].unique())


def convert_tushare_sw_industry_daily(raw, index_code: str | None = None):
    """Convert raw Tushare sw_daily rows into the local sw_industry_daily schema."""
    return convert_mapped_frame(
        raw,
        FIELD_MAP,
        SW_INDUSTRY_DAILY_COLUMNS,
        sort_columns=["industry_index_code", "trade_date"],
        date_columns=["trade_date"],
        scales=SCALES,
        code_fields=(),
        code_column=None,
    )


def run_sw_industry_daily_etl(
    token: str,
    index_codes,
    start_date: str | None = None,
    end_date: str | None = None,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    raw_output_root: Path = DEFAULT_RAW_OUTPUT_ROOT,
    **kwargs,
) -> dict:
    def fetch_fn(pro, index_code: str):
        return fetch_paginated(pro, "sw_daily", TUSHARE_SW_DAILY_FIELDS, page_size=SW_DAILY_PAGE_SIZE, ts_code=index_code, start_date=start_date, end_date=end_date)

    return run_per_key_etl(
        "fetch_sw_industry_daily",
        token,
        keys=list(index_codes),
        fetch_fn=fetch_fn,
        convert_fn=convert_tushare_sw_industry_daily,
        output_path_fn=lambda index_code: Path(output_root) / f"{index_code}.csv",
        raw_output_path_fn=lambda index_code: Path(raw_output_root) / f"{index_code}.csv",
        **kwargs,
    )


def main() -> int:
    args = parse_args()
    if not require_token(args):
        return 2
    try:
        index_codes = args.index_codes or load_industry_codes(args.classification, args.levels)
    except Exception as exc:
        print(f"fetch_sw_industry_daily failed: {exc}", file=sys.stderr)
        return 1
    return run_main(
        "fetch_sw_industry_daily",
        lambda: run_sw_industry_daily_etl(
            token=args.token,
            index_codes=index_codes,
            start_date=args.start_date,
            end_date=args.end_date,
            output_root=args.output_root,
            raw_output_root=args.raw_output_root,
            write_raw=args.with_raw,
            **run_control_kwargs(args),
        ),
        unit="industry indices",
    )


if __name__ == "__main__":
    raise SystemExit(main())
