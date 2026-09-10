#!/usr/bin/env python3
"""Fetch Shenwan industry classification and membership history from Tushare.

Outputs:
data/metadata/sw_industry.csv          (classification tree)
data/metadata/sw_industry_member.csv   (stock membership with in/out dates)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.industry import (
    DEFAULT_SW_SOURCE,
    SW_INDUSTRY_COLUMNS,
    SW_INDUSTRY_MEMBER_COLUMNS,
    SW_INDUSTRY_MEMBER_PAGE_SIZE,
    SW_LEVELS,
    TUSHARE_INDEX_CLASSIFY_FIELDS,
    TUSHARE_INDEX_MEMBER_FIELD_MAP,
    TUSHARE_INDEX_MEMBER_FIELDS,
)
from a_share_db.constant.paths import RAW_TUSHARE_ROOT, SW_INDUSTRY_MEMBER_PATH, SW_INDUSTRY_PATH
from a_share_db.utils.cli import (
    add_run_control_arguments,
    add_token_argument,
    report_result,
    require_token,
    run_control_kwargs,
)
from a_share_db.utils.etl_common import convert_mapped_frame, fetch_paginated, import_pandas
from a_share_db.utils.etl_runners import run_single_table_etl


CLASSIFY_FIELD_MAP = dict(zip(TUSHARE_INDEX_CLASSIFY_FIELDS, SW_INDUSTRY_COLUMNS))
SW_TABLES = ["classification", "member"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Tushare index_classify and index_member_all for Shenwan industries."
    )
    add_token_argument(parser)
    parser.add_argument("--tables", nargs="+", choices=SW_TABLES, default=SW_TABLES, help="Tables to fetch. Default: classification member.")
    parser.add_argument("--source", default=DEFAULT_SW_SOURCE, help=f"Shenwan classification version. Default: {DEFAULT_SW_SOURCE}.")
    parser.add_argument("--output", type=Path, default=SW_INDUSTRY_PATH, help=f"Classification output CSV. Default: {SW_INDUSTRY_PATH}")
    parser.add_argument("--member-output", type=Path, default=SW_INDUSTRY_MEMBER_PATH, help=f"Membership output CSV. Default: {SW_INDUSTRY_MEMBER_PATH}")
    parser.add_argument("--with-raw", action="store_true", help="Also write raw provider CSV files under data/raw/tushare/.")
    add_run_control_arguments(parser, resumable=False, loops=False)
    return parser.parse_args()


def build_classification_fetcher(source: str):
    def fetch_classification(pro):
        pd = import_pandas()
        frames = [
            fetch_paginated(pro, "index_classify", TUSHARE_INDEX_CLASSIFY_FIELDS, src=source, level=level)
            for level in SW_LEVELS
        ]
        return pd.concat(frames, ignore_index=True).drop_duplicates(subset=["index_code"], keep="last")

    return fetch_classification


def convert_tushare_sw_industry(raw):
    """Convert raw Tushare index_classify rows into the local sw_industry schema."""
    return convert_mapped_frame(
        raw,
        CLASSIFY_FIELD_MAP,
        SW_INDUSTRY_COLUMNS,
        sort_columns=["level", "industry_index_code"],
        code_fields=(),
        code_column=None,
    )


def build_member_fetcher(l1_codes: list[str]):
    def fetch_members(pro):
        pd = import_pandas()
        # The full-market query is capped, so members are pulled per L1 industry.
        frames = [
            fetch_paginated(pro, "index_member_all", TUSHARE_INDEX_MEMBER_FIELDS, page_size=SW_INDUSTRY_MEMBER_PAGE_SIZE, l1_code=l1_code)
            for l1_code in l1_codes
        ]
        frame = pd.concat(frames, ignore_index=True)
        return frame.drop_duplicates(subset=["ts_code", "l3_code", "in_date"], keep="last")

    return fetch_members


def convert_tushare_sw_industry_member(raw):
    """Convert raw Tushare index_member_all rows into the local sw_industry_member schema."""
    return convert_mapped_frame(
        raw,
        TUSHARE_INDEX_MEMBER_FIELD_MAP,
        SW_INDUSTRY_MEMBER_COLUMNS,
        sort_columns=["code", "in_date"],
        date_columns=["in_date", "out_date"],
    )


def run_sw_industry_etl(token: str, source: str = DEFAULT_SW_SOURCE, output_path: Path = SW_INDUSTRY_PATH, **kwargs) -> dict:
    return run_single_table_etl(
        "fetch_sw_industry",
        token,
        build_classification_fetcher(source),
        convert_tushare_sw_industry,
        output_path=output_path,
        raw_output_path=RAW_TUSHARE_ROOT / "sw_industry.csv",
        **kwargs,
    )


def run_sw_industry_member_etl(token: str, classification_path: Path = SW_INDUSTRY_PATH, output_path: Path = SW_INDUSTRY_MEMBER_PATH, **kwargs) -> dict:
    pd = import_pandas()
    classification_path = Path(classification_path)
    if not classification_path.exists():
        raise FileNotFoundError(f"Missing classification file, fetch it first: {classification_path}")
    classification = pd.read_csv(classification_path, dtype=str).fillna("")
    l1_codes = sorted(classification.loc[classification["level"].eq("L1"), "industry_index_code"].unique())
    return run_single_table_etl(
        "fetch_sw_industry_member",
        token,
        build_member_fetcher(l1_codes),
        convert_tushare_sw_industry_member,
        output_path=output_path,
        raw_output_path=RAW_TUSHARE_ROOT / "sw_industry_member.csv",
        **kwargs,
    )


def main() -> int:
    args = parse_args()
    if not require_token(args):
        return 2
    control = run_control_kwargs(args)
    exit_code = 0
    try:
        if "classification" in args.tables:
            result = run_sw_industry_etl(token=args.token, source=args.source, output_path=args.output, write_raw=args.with_raw, **control)
            exit_code = max(exit_code, report_result(result, "fetch_sw_industry"))
        if "member" in args.tables:
            result = run_sw_industry_member_etl(token=args.token, classification_path=args.output, output_path=args.member_output, write_raw=args.with_raw, **control)
            exit_code = max(exit_code, report_result(result, "fetch_sw_industry_member"))
    except Exception as exc:
        print(f"fetch_sw_industry failed: {exc}", file=sys.stderr)
        return 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
