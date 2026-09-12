#!/usr/bin/env python3
"""Fetch any table registered in a_share_db.constant.table_registry.

Examples:
  python3 a_share_db/scripts/warehouse/fetch_tables.py --list
  python3 a_share_db/scripts/warehouse/fetch_tables.py --tables broker_report --start-date 20240101 --dry-run
  python3 a_share_db/scripts/warehouse/fetch_tables.py --tiers 1 --resume
  python3 a_share_db/scripts/warehouse/fetch_tables.py --groups fund --update
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.table_registry import TABLE_GROUPS, TABLE_SPECS, TIER_ONE_TABLES, TIER_TWO_TABLES
from a_share_db.utils.cli import (
    add_date_range_arguments,
    add_run_control_arguments,
    add_stock_selection_arguments,
    add_token_argument,
    report_result,
    require_token,
    run_control_kwargs,
    stock_selection_kwargs,
)
from a_share_db.utils.table_runner import DEFAULT_REFRESH_RECENT_DAYS, run_registered_table


TIERS = {"1": TIER_ONE_TABLES, "2": TIER_TWO_TABLES}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch registered Tushare tables through the generic table runner.")
    add_token_argument(parser)
    parser.add_argument("--tables", nargs="+", choices=list(TABLE_SPECS), metavar="TABLE", help="Table names (see --list).")
    parser.add_argument("--groups", nargs="+", choices=list(TABLE_GROUPS), help="Table groups: " + " ".join(TABLE_GROUPS))
    parser.add_argument("--tiers", nargs="+", choices=list(TIERS), help="Priority tiers: 1 (core) and/or 2 (strategy dependent).")
    parser.add_argument("--list", action="store_true", help="Print registered tables and exit.")
    add_stock_selection_arguments(parser)
    add_date_range_arguments(parser, default_start=None, end_defaults_to_today=True)
    parser.add_argument("--limit-keys", type=int, help="Fetch only the first N keys/periods/years of per-key layouts. Useful for smoke tests.")
    parser.add_argument("--refresh-recent-days", type=int, default=DEFAULT_REFRESH_RECENT_DAYS, help=f"With --resume, report periods ending within this many days are re-fetched. Default: {DEFAULT_REFRESH_RECENT_DAYS}.")
    add_run_control_arguments(parser, incremental=True)
    parser.set_defaults(all_stocks=True)
    return parser.parse_args()


def selected_tables(args: argparse.Namespace) -> list[str]:
    names: list[str] = []
    for tier in args.tiers or []:
        names.extend(TIERS[tier])
    for group in args.groups or []:
        names.extend(TABLE_GROUPS[group])
    names.extend(args.tables or [])
    ordered = []
    for name in names:
        if name not in ordered:
            ordered.append(name)
    return ordered


def main() -> int:
    args = parse_args()
    if args.list:
        for name, spec in TABLE_SPECS.items():
            tier = "1" if name in TIER_ONE_TABLES else "2"
            print(f"{name:26s} tier={tier} group={spec['group']:13s} layout={spec['layout']:10s} api={spec['api']:20s} -> {spec['csv']}")
        return 0
    if not require_token(args):
        return 2
    names = selected_tables(args)
    if not names:
        print("Pass --tables, --groups or --tiers (see --list).", file=sys.stderr)
        return 2
    control = run_control_kwargs(args)
    update = control.pop("incremental", False)
    stock_kwargs = stock_selection_kwargs(args)
    exit_code = 0
    for name in names:
        try:
            result = run_registered_table(
                name,
                args.token,
                start_date=args.start_date,
                end_date=args.end_date,
                update=update,
                refresh_recent_days=args.refresh_recent_days,
                limit_keys=args.limit_keys,
                stock_kwargs=stock_kwargs if TABLE_SPECS[name]["layout"] == "per_stock" else None,
                **control,
            )
        except Exception as exc:
            print(f"fetch_{name} failed: {exc}", file=sys.stderr)
            exit_code = 1
            continue
        exit_code = max(exit_code, report_result(result, f"fetch_{name}"))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
