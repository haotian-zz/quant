#!/usr/bin/env python3
"""Fetch stock index futures data from Tushare.

Outputs:
data/metadata/futures_basic.csv                    (--tables basic)
data/market_data/futures_daily/{contract_code}.csv (--tables daily; every IF/IH/IC/IM contract plus the continuous series)
data/market_data/futures_main_mapping.csv          (--tables mapping; trade_date -> main contract)

Basis against the spot index is not stored; compute it from index_daily and the
continuous series (for example IF.CFX close minus 000300.SH close).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.futures import (
    DEFAULT_CONTINUOUS_CONTRACT_CODES,
    DEFAULT_FUTURES_START_DATE,
    DEFAULT_INDEX_FUTURES_PRODUCTS,
    FUTURES_BASIC_COLUMNS,
    FUTURES_DAILY_COLUMNS,
    FUTURES_DAILY_PAGE_SIZE,
    FUTURES_EXCHANGE,
    FUTURES_MAIN_MAPPING_COLUMNS,
    TUSHARE_FUTURES_AMOUNT_TO_LOCAL,
    TUSHARE_FUTURES_BASIC_FIELD_MAP,
    TUSHARE_FUTURES_BASIC_FIELDS,
    TUSHARE_FUTURES_DAILY_FIELD_MAP,
    TUSHARE_FUTURES_DAILY_FIELDS,
    TUSHARE_FUTURES_MAPPING_FIELD_MAP,
    TUSHARE_FUTURES_MAPPING_FIELDS,
    TUSHARE_FUTURES_TYPE_FUTURES,
)
from a_share_db.constant.paths import FUTURES_BASIC_PATH, FUTURES_DAILY_ROOT, FUTURES_MAIN_MAPPING_PATH, RAW_TUSHARE_ROOT
from a_share_db.utils.cli import (
    add_date_range_arguments,
    add_run_control_arguments,
    add_token_argument,
    report_result,
    require_token,
    run_control_kwargs,
)
from a_share_db.utils.etl_common import convert_mapped_frame, fetch_paginated, import_pandas
from a_share_db.utils.etl_runners import run_per_key_etl, run_single_table_etl


FUTURES_TABLES = ["basic", "daily", "mapping"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Tushare CFFEX stock index futures: contracts, daily quotes, main-contract mapping.")
    add_token_argument(parser)
    parser.add_argument("--tables", nargs="+", choices=FUTURES_TABLES, default=FUTURES_TABLES, help="Tables to fetch. Default: basic daily mapping.")
    parser.add_argument("--products", nargs="+", default=DEFAULT_INDEX_FUTURES_PRODUCTS, help="Futures product codes. Default: IF IH IC IM.")
    parser.add_argument("--contract-codes", nargs="+", help="Explicit contract codes for --tables daily, for example IF2609.CFX IF.CFX. Default: all contracts of --products from futures_basic.csv plus continuous series.")
    add_date_range_arguments(parser, default_start=DEFAULT_FUTURES_START_DATE, end_defaults_to_today=True)
    parser.add_argument("--basic-output", type=Path, default=FUTURES_BASIC_PATH, help=f"Contract master CSV. Default: {FUTURES_BASIC_PATH}")
    parser.add_argument("--output-root", type=Path, default=FUTURES_DAILY_ROOT, help=f"Per-contract daily directory. Default: {FUTURES_DAILY_ROOT}")
    parser.add_argument("--mapping-output", type=Path, default=FUTURES_MAIN_MAPPING_PATH, help=f"Main-contract mapping CSV. Default: {FUTURES_MAIN_MAPPING_PATH}")
    parser.add_argument("--active-only", action="store_true", help="For --tables daily, only contracts not yet delisted at --end-date plus the continuous series. Use for routine refreshes.")
    parser.add_argument("--with-raw", action="store_true", help="Also write raw provider CSV files under data/raw/tushare/.")
    add_run_control_arguments(parser)
    return parser.parse_args()


def build_basic_fetcher(products):
    def fetch(pro):
        frame = fetch_paginated(pro, "fut_basic", TUSHARE_FUTURES_BASIC_FIELDS, exchange=FUTURES_EXCHANGE, fut_type=TUSHARE_FUTURES_TYPE_FUTURES)
        # Only stock index products are kept; CFFEX also lists bond futures.
        return frame[frame["fut_code"].isin(list(products))].drop_duplicates(subset=["ts_code"], keep="last")

    return fetch


def convert_tushare_futures_basic(raw):
    return convert_mapped_frame(
        raw,
        TUSHARE_FUTURES_BASIC_FIELD_MAP,
        FUTURES_BASIC_COLUMNS,
        sort_columns=["product_code", "list_date", "contract_code"],
        date_columns=["list_date", "delist_date", "last_delivery_date"],
        code_fields=(),
        code_column=None,
    )


def convert_tushare_futures_daily(raw, contract_code: str | None = None):
    return convert_mapped_frame(
        raw,
        TUSHARE_FUTURES_DAILY_FIELD_MAP,
        FUTURES_DAILY_COLUMNS,
        sort_columns=["contract_code", "trade_date"],
        date_columns=["trade_date"],
        scales={"amount": TUSHARE_FUTURES_AMOUNT_TO_LOCAL},
        code_fields=(),
        code_column=None,
    )


def build_mapping_fetcher(continuous_codes, start_date, end_date):
    def fetch(pro):
        pd = import_pandas()
        frames = [
            fetch_paginated(pro, "fut_mapping", TUSHARE_FUTURES_MAPPING_FIELDS, page_size=FUTURES_DAILY_PAGE_SIZE, ts_code=code, start_date=start_date, end_date=end_date)
            for code in continuous_codes
        ]
        return pd.concat(frames, ignore_index=True).drop_duplicates(subset=["ts_code", "trade_date"], keep="last")

    return fetch


def convert_tushare_futures_mapping(raw):
    return convert_mapped_frame(
        raw,
        TUSHARE_FUTURES_MAPPING_FIELD_MAP,
        FUTURES_MAIN_MAPPING_COLUMNS,
        sort_columns=["continuous_code", "trade_date"],
        date_columns=["trade_date"],
        code_fields=(),
        code_column=None,
    )


def load_contract_codes(basic_path: Path, products, active_on: str | None = None) -> list[str]:
    pd = import_pandas()
    basic_path = Path(basic_path)
    if not basic_path.exists():
        raise FileNotFoundError(f"Missing futures_basic file, fetch it first: {basic_path}")
    frame = pd.read_csv(basic_path, dtype=str).fillna("")
    frame = frame[frame["product_code"].isin(list(products))]
    if active_on:
        # Delisted contracts never change again, so routine refreshes skip them.
        active_on_iso = f"{active_on[:4]}-{active_on[4:6]}-{active_on[6:8]}" if len(active_on) == 8 else active_on
        frame = frame[(frame["delist_date"] == "") | (frame["delist_date"] >= active_on_iso)]
    contracts = sorted(frame["contract_code"].unique())
    continuous = [f"{product}.CFX" for product in products]
    return continuous + contracts


def run_futures_basic_etl(token: str, products=DEFAULT_INDEX_FUTURES_PRODUCTS, output_path: Path = FUTURES_BASIC_PATH, **kwargs) -> dict:
    return run_single_table_etl("fetch_futures_basic", token, build_basic_fetcher(products), convert_tushare_futures_basic, output_path=output_path, raw_output_path=RAW_TUSHARE_ROOT / "futures_basic.csv", **kwargs)


def run_futures_mapping_etl(token: str, continuous_codes=DEFAULT_CONTINUOUS_CONTRACT_CODES, start_date: str | None = None, end_date: str | None = None, output_path: Path = FUTURES_MAIN_MAPPING_PATH, **kwargs) -> dict:
    start_date = start_date or DEFAULT_FUTURES_START_DATE
    return run_single_table_etl("fetch_futures_main_mapping", token, build_mapping_fetcher(continuous_codes, start_date, end_date), convert_tushare_futures_mapping, output_path=output_path, raw_output_path=RAW_TUSHARE_ROOT / "futures_main_mapping.csv", **kwargs)


def run_futures_daily_etl(token: str, contract_codes, start_date: str | None = None, end_date: str | None = None, output_root: Path = FUTURES_DAILY_ROOT, **kwargs) -> dict:
    start_date = start_date or DEFAULT_FUTURES_START_DATE

    def fetch_fn(pro, contract_code: str):
        return fetch_paginated(pro, "fut_daily", TUSHARE_FUTURES_DAILY_FIELDS, page_size=FUTURES_DAILY_PAGE_SIZE, ts_code=contract_code, start_date=start_date, end_date=end_date)

    return run_per_key_etl(
        "fetch_futures_daily",
        token,
        keys=list(contract_codes),
        fetch_fn=fetch_fn,
        convert_fn=convert_tushare_futures_daily,
        output_path_fn=lambda code: Path(output_root) / f"{code}.csv",
        raw_output_path_fn=lambda code: RAW_TUSHARE_ROOT / "futures_daily" / f"{code}.csv",
        **kwargs,
    )


def main() -> int:
    args = parse_args()
    if not require_token(args):
        return 2
    control = run_control_kwargs(args)
    single = {key: control[key] for key in ("dry_run", "write_log", "backup_root", "create_backup", "max_retries", "retry_interval")}
    exit_code = 0
    try:
        if "basic" in args.tables:
            result = run_futures_basic_etl(args.token, products=args.products, output_path=args.basic_output, write_raw=args.with_raw, **single)
            exit_code = max(exit_code, report_result(result, "fetch_futures_basic"))
        if "mapping" in args.tables:
            result = run_futures_mapping_etl(args.token, continuous_codes=[f"{p}.CFX" for p in args.products], start_date=args.start_date, end_date=args.end_date, output_path=args.mapping_output, write_raw=args.with_raw, **single)
            exit_code = max(exit_code, report_result(result, "fetch_futures_main_mapping"))
        if "daily" in args.tables:
            codes = args.contract_codes or load_contract_codes(args.basic_output, args.products, args.end_date if args.active_only else None)
            result = run_futures_daily_etl(args.token, codes, start_date=args.start_date, end_date=args.end_date, output_root=args.output_root, write_raw=args.with_raw, **control)
            exit_code = max(exit_code, report_result(result, "fetch_futures_daily", unit="contracts"))
    except Exception as exc:
        print(f"fetch_futures failed: {exc}", file=sys.stderr)
        return 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
