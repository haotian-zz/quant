#!/usr/bin/env python3
"""One-command historical build for the second-generation Tushare tables.

Steps run in priority order and every step uses --resume semantics, so the
command can be rerun after failures. Use --groups to run a subset:

  metadata   name history, company profiles, IPOs, stock-connect list, index/industry metadata, macro
  index      benchmark index quotes, valuation, weights, Shenwan industry quotes
  financial  statements, indicators, forecasts, express, disclosure dates, top-10 holders
  stock      per-stock tables: limit prices, money flow, margin, northbound holdings, dividends, holder counts
  daily      per-trade-date tables: suspensions, ST list, dragon-tiger list, block trades, limit stats
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.commands import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_PROGRESS_EVERY,
    DEFAULT_REQUEST_INTERVAL,
    DEFAULT_RETRY_INTERVAL,
)
from a_share_db.scripts.financial.fetch_dividend import run_dividend_etl
from a_share_db.scripts.financial.fetch_financial_statements import TABLE_SPECS as FINANCIAL_TABLES, run_financial_table_etl
from a_share_db.scripts.financial.fetch_holder_number import run_holder_number_etl
from a_share_db.scripts.financial.fetch_top10_holders import HOLDER_TABLES, run_top10_holders_etl
from a_share_db.scripts.index.fetch_index_basic import run_index_basic_etl
from a_share_db.scripts.index.fetch_index_daily import INDEX_TABLES, run_index_table_etl
from a_share_db.scripts.index.fetch_index_weight import run_index_weight_etl
from a_share_db.scripts.index.fetch_sw_industry import run_sw_industry_etl, run_sw_industry_member_etl
from a_share_db.scripts.index.fetch_sw_industry_daily import load_industry_codes, run_sw_industry_daily_etl
from a_share_db.scripts.macro.fetch_macro import MACRO_TABLES, run_macro_table_etl
from a_share_db.scripts.market.fetch_limit_price import run_limit_price_etl
from a_share_db.scripts.market.fetch_margin import run_margin_etl, run_margin_summary_etl
from a_share_db.scripts.market.fetch_market_events import EVENT_TABLES, run_market_event_etl
from a_share_db.scripts.market.fetch_moneyflow import run_moneyflow_etl
from a_share_db.scripts.market.fetch_st_stock import run_st_stock_etl
from a_share_db.scripts.market.fetch_stock_connect_flow import run_stock_connect_flow_etl
from a_share_db.scripts.market.fetch_stock_connect_hold import run_stock_connect_hold_etl
from a_share_db.scripts.market.fetch_suspend import run_suspend_etl
from a_share_db.scripts.metadata.fetch_ipo import run_ipo_etl
from a_share_db.scripts.metadata.fetch_name_change import run_name_change_etl
from a_share_db.scripts.metadata.fetch_stock_company import run_stock_company_etl
from a_share_db.scripts.metadata.fetch_stock_connect_constituent import run_stock_connect_constituent_etl
from a_share_db.constant.paths import SW_INDUSTRY_PATH


GROUPS = ["metadata", "index", "financial", "stock", "daily"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build every second-generation table with resume semantics.")
    parser.add_argument("--token", default=os.getenv("TUSHARE_TOKEN"), help="Tushare token. Defaults to env var TUSHARE_TOKEN.")
    parser.add_argument("--groups", nargs="+", choices=GROUPS, default=GROUPS, help="Table groups to build. Default: all, in priority order.")
    parser.add_argument("--end-date", default=datetime.now().strftime("%Y%m%d"), help="End date in YYYYMMDD format. Default: today.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and convert data, but do not write CSV files or logs.")
    parser.add_argument("--no-resume", dest="resume", action="store_false", help="Re-fetch outputs that already exist. Default: resume.")
    parser.add_argument("--update", action="store_true", help="Bring existing tables to --end-date: per-stock trade_date tables extend incrementally, dividend/holder_number are refreshed in full.")
    parser.add_argument("--request-interval", type=float, default=DEFAULT_REQUEST_INTERVAL, help=f"Seconds between provider requests. Default: {DEFAULT_REQUEST_INTERVAL}.")
    parser.add_argument("--progress-every", type=int, default=DEFAULT_PROGRESS_EVERY, help=f"Print progress every N items. Default: {DEFAULT_PROGRESS_EVERY}.")
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES, help=f"Maximum attempts per request. Default: {DEFAULT_MAX_RETRIES}.")
    parser.add_argument("--retry-interval", type=float, default=DEFAULT_RETRY_INTERVAL, help=f"Seconds between retries. Default: {DEFAULT_RETRY_INTERVAL}.")
    parser.set_defaults(resume=True)
    return parser.parse_args()


def build_steps(args: argparse.Namespace) -> list[tuple[str, str, callable]]:
    """Return (group, step name, callable) in priority order."""
    single = {"dry_run": args.dry_run, "max_retries": args.max_retries, "retry_interval": args.retry_interval}
    loop = {
        **single,
        "resume": args.resume,
        "request_interval": args.request_interval,
        "progress_every": args.progress_every,
    }
    token = args.token
    end_date = args.end_date
    steps: list[tuple[str, str, callable]] = []

    # Metadata and small reference tables are cheap and unblock everything else.
    steps += [
        ("metadata", "stock_name_history", lambda: run_name_change_etl(token, **single)),
        ("metadata", "stock_company", lambda: run_stock_company_etl(token, **single)),
        ("metadata", "ipo", lambda: run_ipo_etl(token, end_date=end_date, **single)),
        ("metadata", "stock_connect_constituent", lambda: run_stock_connect_constituent_etl(token, **single)),
        ("metadata", "index_basic", lambda: run_index_basic_etl(token, **single)),
        ("metadata", "sw_industry", lambda: run_sw_industry_etl(token, **single)),
        ("metadata", "sw_industry_member", lambda: run_sw_industry_member_etl(token, **single)),
        ("metadata", "stock_connect_flow", lambda: run_stock_connect_flow_etl(token, end_date=end_date, **single)),
        ("metadata", "margin_summary", lambda: run_margin_summary_etl(token, end_date=end_date, **single)),
    ]
    steps += [
        ("metadata", f"macro_{table}", (lambda table=table: run_macro_table_etl(table, token, end_date=end_date, **single)))
        for table in MACRO_TABLES
    ]

    # Benchmarks, universes and industry indices. Per-index files have no
    # incremental path yet, so update mode re-fetches them in full.
    index_loop = {**loop, "resume": loop["resume"] and not args.update}
    steps += [
        ("index", f"index_{table}", (lambda table=table: run_index_table_etl(table, token, end_date=end_date, **index_loop)))
        for table in INDEX_TABLES
    ]
    steps.append(("index", "index_weight", lambda: run_index_weight_etl(token, end_date=end_date, **index_loop)))
    steps.append(
        (
            "index",
            "sw_industry_daily",
            lambda: run_sw_industry_daily_etl(token, load_industry_codes(SW_INDUSTRY_PATH, ["L1", "L2", "L3"]), end_date=end_date, **index_loop),
        )
    )

    # Fundamentals by report period.
    steps += [
        ("financial", table, (lambda table=table: run_financial_table_etl(table, token, end_date=end_date, **loop)))
        for table in FINANCIAL_TABLES
    ]
    steps += [
        ("financial", f"top10_{table}", (lambda table=table: run_top10_holders_etl(table, token, end_date=end_date, **loop)))
        for table in HOLDER_TABLES
    ]

    # Per-stock tables; each is one request per listed stock.
    # In update mode trade_date tables extend from their local max date; the two
    # announcement-keyed tables have no date filter and are refreshed in full.
    series = {**loop, "incremental": args.update}
    refresh = {**loop, "resume": loop["resume"] and not args.update}
    steps += [
        ("stock", "limit_price", lambda: run_limit_price_etl(token, all_stocks=True, end_date=end_date, **series)),
        ("stock", "moneyflow", lambda: run_moneyflow_etl(token, all_stocks=True, end_date=end_date, **series)),
        ("stock", "margin", lambda: run_margin_etl(token, all_stocks=True, end_date=end_date, **series)),
        ("stock", "stock_connect_hold", lambda: run_stock_connect_hold_etl(token, all_stocks=True, end_date=end_date, **series)),
        ("stock", "dividend", lambda: run_dividend_etl(token, all_stocks=True, **refresh)),
        ("stock", "holder_number", lambda: run_holder_number_etl(token, all_stocks=True, **refresh)),
    ]

    # Per-trade-date tables; each is one request per trading day.
    steps += [
        ("daily", "suspend", lambda: run_suspend_etl(token, start_date=None, end_date=end_date, **loop)),
        ("daily", "st_stock", lambda: run_st_stock_etl(token, start_date=None, end_date=end_date, **loop)),
    ]
    steps += [
        ("daily", table, (lambda table=table: run_market_event_etl(table, token, end_date=end_date, **loop)))
        for table in EVENT_TABLES
    ]
    return steps


def main() -> int:
    args = parse_args()
    if not args.token:
        print("Tushare token is required. Set TUSHARE_TOKEN or pass --token.", file=sys.stderr)
        return 2

    failures = []
    for group, name, step in build_steps(args):
        if group not in args.groups:
            continue
        started = datetime.now()
        print(f"[{started:%H:%M:%S}] {group}/{name} started", flush=True)
        try:
            result = step()
        except Exception as exc:
            # Keep building the remaining tables; the summary lists what to rerun.
            failures.append((name, str(exc)))
            print(f"[{datetime.now():%H:%M:%S}] {group}/{name} FAILED: {exc}", file=sys.stderr, flush=True)
            continue
        status = result.get("status", "")
        if status != "success":
            failures.append((name, result.get("error_message", status)))
        print(
            f"[{datetime.now():%H:%M:%S}] {group}/{name} {status}: rows={result.get('row_count', 0)} "
            f"skipped={result.get('skipped_count', 0)} failed={result.get('failure_count', 0)}",
            flush=True,
        )

    if failures:
        print("Steps needing attention:", file=sys.stderr)
        for name, message in failures:
            print(f"  {name}: {message[:300]}", file=sys.stderr)
        return 1
    print("Extended history build completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
