#!/usr/bin/env python3
"""Build coarser minute frequencies and adjusted minute bars from local data.

No provider API is called. Inputs are local unadjusted minute files plus the
daily adjustment factors:

data/market_data/minute/{source}/none/{code}.csv  +  data/market_data/adj_factor/{code}.csv

Outputs:
data/market_data/minute/{frequency}/none/{code}.csv   resampled from the source frequency
data/market_data/minute/{frequency}/qfq/{code}.csv    prices scaled by adjust_factor / latest_factor
data/market_data/minute/{frequency}/hfq/{code}.csv    prices scaled by adjust_factor

Bars are bucketed by session (09:30-11:30, 13:00-15:00) so 15m/30m/60m bar end
times land on 09:45 ... 11:30 and 13:15 ... 15:00. Volume and amount are summed
and never adjusted, matching build_adjusted_daily.
"""

from __future__ import annotations

import argparse
import io
import os
import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.daily import ADJ_FACTOR_COLUMNS, ADJUST_TYPES
from a_share_db.constant.minute import MINUTE_BAR_COLUMNS, MINUTE_FREQUENCIES
from a_share_db.constant.paths import ADJ_FACTOR_ROOT, BACKUP_ROOT, ETL_LOG_PATH, MINUTE_ROOT, STOCK_BASIC_PATH
from a_share_db.utils.cli import add_run_control_arguments, add_stock_selection_arguments, run_control_kwargs, run_main, stock_selection_kwargs
from a_share_db.utils.etl_common import (
    import_pandas,
    load_requested_codes,
    now_text,
    read_existing_csv,
    read_stock_basic,
    select_stock_rows,
)
from a_share_db.scripts.market.fetch_minute import append_minute_rows, read_last_bar_end_time
from a_share_db.utils.etl_runners import EtlRun
from a_share_db.utils.progress import ProgressReporter


DEFAULT_SOURCE_FREQUENCY = "1m"
DEFAULT_TARGET_FREQUENCIES = ["15m", "30m", "60m"]
DEFAULT_ADJUST_TYPES = ["hfq", "qfq"]
FREQUENCY_MINUTES = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "60m": 60}
# A-share sessions in minutes since midnight: (session start, session end).
SESSIONS = [(9 * 60 + 30, 11 * 60 + 30), (13 * 60, 15 * 60)]
PRICE_COLUMNS = ["open", "high", "low", "close"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resample local minute bars and build qfq/hfq minute files.")
    add_stock_selection_arguments(parser)
    parser.add_argument("--source-frequency", choices=MINUTE_FREQUENCIES, default=DEFAULT_SOURCE_FREQUENCY, help=f"Local frequency to resample from. Default: {DEFAULT_SOURCE_FREQUENCY}.")
    parser.add_argument("--frequencies", nargs="+", choices=MINUTE_FREQUENCIES, default=DEFAULT_TARGET_FREQUENCIES, help="Frequencies to build. The source frequency itself may be listed to build only its adjusted files. Default: 15m 30m 60m.")
    parser.add_argument("--adjust-types", nargs="+", choices=ADJUST_TYPES, default=["none"] + DEFAULT_ADJUST_TYPES, help="Outputs per frequency. Default: none hfq qfq.")
    parser.add_argument("--minute-root", type=Path, default=MINUTE_ROOT, help=f"Minute data root. Default: {MINUTE_ROOT}")
    parser.add_argument("--adj-factor-root", type=Path, default=ADJ_FACTOR_ROOT, help=f"Adjustment factor directory. Default: {ADJ_FACTOR_ROOT}")
    add_run_control_arguments(parser, loops=False)
    parser.add_argument("--progress-every", type=int, default=50, help="Print progress every N stocks. Default: 50.")
    parser.add_argument("--stop-on-error", action="store_true", help="Stop on the first failure.")
    parser.add_argument(
        "--update",
        action="store_true",
        help=(
            "Append only bars after each existing none/hfq file's last bar_end_time, reading just the "
            "tail of the source file. qfq files are skipped because they must be rebuilt when the latest factor changes."
        ),
    )
    return parser.parse_args()


# Tail bytes read from the source file in update mode; enough for several weeks of 5m bars.
SOURCE_TAIL_BYTES = 4 * 1024 * 1024


def read_source_tail(path: Path, after_date: str):
    """Return source bars with trade_date > after_date, reading only the file tail when possible."""
    pd = import_pandas()
    size = path.stat().st_size
    with path.open("rb") as handle:
        header = handle.readline().decode("utf-8")
        if size > SOURCE_TAIL_BYTES:
            handle.seek(size - SOURCE_TAIL_BYTES)
            chunk = handle.read().decode("utf-8", errors="ignore")
            # Drop the partial first line of the chunk.
            chunk = chunk.split("\n", 1)[1] if "\n" in chunk else ""
        else:
            chunk = handle.read().decode("utf-8", errors="ignore")
    frame = pd.read_csv(io.StringIO(header + chunk), dtype={"code": str, "trade_date": str, "bar_end_time": str})
    if size > SOURCE_TAIL_BYTES and not frame.empty and frame["trade_date"].iloc[0] > after_date:
        # The gap is longer than the tail covers; fall back to the whole file.
        frame = pd.read_csv(path, dtype={"code": str, "trade_date": str, "bar_end_time": str})
    return frame[frame["trade_date"] > after_date]


def bucket_end_minutes(minutes_of_day, step: int):
    """Map bar end times (minutes since midnight) to the enclosing bucket end."""
    pd = import_pandas()
    result = pd.Series(index=minutes_of_day.index, dtype="float64")
    morning_start, morning_end = SESSIONS[0]
    afternoon_start, afternoon_end = SESSIONS[1]
    is_morning = minutes_of_day <= morning_end
    for mask, start, end in ((is_morning, morning_start, morning_end), (~is_morning, afternoon_start, afternoon_end)):
        offset = (minutes_of_day[mask] - start).clip(lower=1)
        # ceil(offset / step) buckets; the opening auction bar (offset 0) joins bucket 1.
        buckets = ((offset + step - 1) // step).clip(lower=1)
        result[mask] = (start + buckets * step).clip(upper=end)
    return result.astype("int64")


def resample_minute_bars(source, frequency: str):
    """Aggregate unadjusted minute bars to a coarser frequency."""
    pd = import_pandas()
    step = FREQUENCY_MINUTES[frequency]
    frame = source.copy()
    timestamps = pd.to_datetime(frame["bar_end_time"], errors="coerce")
    frame = frame[timestamps.notna()]
    timestamps = timestamps[timestamps.notna()]
    minutes_of_day = timestamps.dt.hour * 60 + timestamps.dt.minute
    bucket_end = bucket_end_minutes(minutes_of_day, step)
    frame["__bucket"] = timestamps.dt.normalize() + pd.to_timedelta(bucket_end, unit="m")
    for column in PRICE_COLUMNS + ["volume", "amount"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.sort_values("bar_end_time", kind="stable")
    grouped = frame.groupby("__bucket", sort=True)
    output = grouped.agg(
        code=("code", "first"),
        name=("name", "first"),
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
        amount=("amount", "sum"),
    ).reset_index()
    output["bar_end_time"] = output["__bucket"].dt.strftime("%Y-%m-%d %H:%M:%S")
    output["trade_date"] = output["__bucket"].dt.strftime("%Y-%m-%d")
    output["frequency"] = frequency
    output["adjust_type"] = "none"
    output["update_time"] = now_text()
    return output[MINUTE_BAR_COLUMNS]


def adjust_minute_bars(none_bars, adj_factor, adjust_type: str):
    """Scale minute prices by the daily adjustment factor of their trade date."""
    pd = import_pandas()
    factors = adj_factor[["trade_date", "adjust_factor"]].copy()
    factors["adjust_factor"] = pd.to_numeric(factors["adjust_factor"], errors="coerce")
    factors = factors.dropna().drop_duplicates(subset=["trade_date"], keep="last").sort_values("trade_date")
    if factors.empty:
        return none_bars.iloc[0:0].copy()
    # Inner join drops days without a factor, matching the daily builder.
    merged = none_bars.merge(factors, on="trade_date", how="inner")
    if adjust_type == "qfq":
        # qfq anchors to the latest local factor, so files are rebuilt when it changes.
        multiplier = merged["adjust_factor"] / factors["adjust_factor"].iloc[-1]
    else:
        multiplier = merged["adjust_factor"]
    for column in PRICE_COLUMNS:
        merged[column] = pd.to_numeric(merged[column], errors="coerce") * multiplier
    merged["adjust_type"] = adjust_type
    merged["update_time"] = now_text()
    return merged[MINUTE_BAR_COLUMNS]


def run_build_minute_derived(
    codes=None,
    codes_file=None,
    all_stocks: bool = False,
    stock_basic_path: Path = STOCK_BASIC_PATH,
    statuses=("listed",),
    limit_stocks: int | None = None,
    source_frequency: str = DEFAULT_SOURCE_FREQUENCY,
    frequencies=DEFAULT_TARGET_FREQUENCIES,
    adjust_types=("none", "hfq", "qfq"),
    minute_root: Path = MINUTE_ROOT,
    adj_factor_root: Path = ADJ_FACTOR_ROOT,
    dry_run: bool = False,
    resume: bool = False,
    write_log: bool = True,
    log_path: Path = ETL_LOG_PATH,
    backup_root: Path = BACKUP_ROOT,
    create_backup: bool = False,
    progress_every: int = 0,
    stop_on_error: bool = False,
    max_retries: int = 1,
    retry_interval: float = 0.0,
    incremental: bool = False,
) -> dict:
    pd = import_pandas()
    run = EtlRun("build_minute_derived", log_path, write_log, dry_run, backup_root)
    frequencies = list(frequencies)
    adjust_types = list(adjust_types)
    stock_count = 0
    try:
        stock_basic = read_stock_basic(Path(stock_basic_path), statuses)
        stocks = select_stock_rows(stock_basic, load_requested_codes(codes, codes_file), all_stocks, limit_stocks)
        stock_count = len(stocks)
        progress = ProgressReporter(stock_count, every=progress_every, label="Build minute derived")
        for index, stock in enumerate(stocks.to_dict("records"), start=1):
            code = stock["code"]
            try:
                targets = [
                    (frequency, adjust_type)
                    for frequency in frequencies
                    for adjust_type in adjust_types
                    if not (frequency == source_frequency and adjust_type == "none")
                ]
                source_path = Path(minute_root) / source_frequency / "none" / f"{code}.csv"
                if not source_path.exists() or source_path.stat().st_size == 0:
                    raise FileNotFoundError(f"missing source minute file {source_path}")
                if incremental:
                    # Append mode: extend none/hfq files from their last bar; qfq is left for full rebuilds.
                    pending = [(f, a) for f, a in targets if a != "qfq"]
                    last_by_target = {
                        (f, a): read_last_bar_end_time(Path(minute_root) / f / a / f"{code}.csv") for f, a in pending
                    }
                    pending = [(f, a) for f, a in pending if last_by_target[(f, a)] is not None]
                    if not pending:
                        run.skipped_count += 1
                        continue
                    earliest = min(last_by_target[key] for key in pending).strftime("%Y-%m-%d")
                    source = read_source_tail(source_path, earliest)
                else:
                    pending = [
                        (frequency, adjust_type)
                        for frequency, adjust_type in targets
                        if not (resume and (Path(minute_root) / frequency / adjust_type / f"{code}.csv").exists())
                    ]
                    if not pending:
                        run.skipped_count += 1
                        continue
                    source = pd.read_csv(source_path, dtype={"code": str, "trade_date": str, "bar_end_time": str})
                adj_factor = read_existing_csv(Path(adj_factor_root) / f"{code}.csv", ADJ_FACTOR_COLUMNS, string_columns=("code", "trade_date"))

                none_by_frequency = {source_frequency: source}
                for frequency, adjust_type in pending:
                    if frequency not in none_by_frequency:
                        none_by_frequency[frequency] = resample_minute_bars(source, frequency)
                    none_bars = none_by_frequency[frequency]
                    output = none_bars if adjust_type == "none" else adjust_minute_bars(none_bars, adj_factor, adjust_type)
                    target_path = Path(minute_root) / frequency / adjust_type / f"{code}.csv"
                    if incremental:
                        # Only whole days after the target's last bar are appended, so a partial day is never duplicated.
                        last_date = last_by_target[(frequency, adjust_type)].strftime("%Y-%m-%d")
                        output = output[output["trade_date"] > last_date]
                        if output.empty:
                            continue
                        run.row_count += len(output)
                        if not dry_run:
                            append_minute_rows(output, target_path)
                        continue
                    run.row_count += len(output)
                    run.write(output, target_path, create_backup)
            except Exception as exc:
                run.failures.append({"item": code, "code": code, "error": str(exc)})
                if stop_on_error:
                    raise
            finally:
                progress.maybe_print(index, row_count=run.row_count, skipped_count=run.skipped_count, failure_count=len(run.failures))
        run.finish()
        return run.result(stock_count=stock_count, output_root=str(minute_root))
    except Exception as exc:
        run.fail(exc)
        raise
    finally:
        run.log()


def main() -> int:
    args = parse_args()
    return run_main(
        "build_minute_derived",
        lambda: run_build_minute_derived(
            source_frequency=args.source_frequency,
            frequencies=args.frequencies,
            adjust_types=args.adjust_types,
            minute_root=args.minute_root,
            adj_factor_root=args.adj_factor_root,
            **stock_selection_kwargs(args),
            **run_control_kwargs(args),
        ),
        unit="stocks",
    )


if __name__ == "__main__":
    raise SystemExit(main())
