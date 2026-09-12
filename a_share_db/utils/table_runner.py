"""Execute a table spec from a_share_db.constant.table_registry.

The runner turns a declarative spec into calls of the shared ETL loops in
etl_runners. Scripts stay thin: they pick specs and pass control flags.
"""

from __future__ import annotations

import time
from datetime import date, datetime, timedelta
from pathlib import Path

from a_share_db.constant.paths import FUTURES_BASIC_PATH, TRADE_CALENDAR_PATH
from a_share_db.constant.table_registry import TABLE_SPECS
from a_share_db.utils.etl_common import (
    convert_mapped_frame,
    fetch_paginated,
    import_pandas,
    iter_date_windows,
    iter_report_periods,
    parse_date_arg,
    read_trading_days,
)
from a_share_db.utils.etl_runners import (
    run_per_date_etl,
    run_per_key_etl,
    run_per_stock_etl,
    run_single_table_etl,
)


DEFAULT_REFRESH_RECENT_DAYS = 400


# ---------------------------------------------------------------------------
# Conversion
# ---------------------------------------------------------------------------


def convert_spec_frame(spec: dict, raw, constants: dict | None = None):
    """Convert one raw provider frame with the spec's mapping rules."""
    frame = convert_mapped_frame(
        raw,
        spec["field_map"],
        spec["columns"],
        sort_columns=spec["sort_columns"],
        date_columns=spec["date_columns"],
        scales=spec["scales"],
        value_maps=spec["value_maps"],
        code_fields=spec["code_fields"],
        code_column=spec["code_column"],
        constants=constants,
    )
    if spec["dedupe_keys"]:
        frame = frame.drop_duplicates(subset=spec["dedupe_keys"], keep="last").reset_index(drop=True)
    return frame


def _fetch_pages(pro, spec: dict, request_interval: float, **params):
    return fetch_paginated(
        pro,
        spec["api"],
        spec["field_map"].keys(),
        page_size=spec["page_size"],
        request_interval=request_interval,
        **params,
    )


def _param_loops(spec: dict) -> list[dict]:
    loops = spec["param_loops"] or [{"params": {}}]
    return [{"params": dict(loop.get("params", {})), "constants": dict(loop.get("constants", {}))} for loop in loops]


def _fetch_and_convert(pro, spec: dict, request_interval: float, base_params: dict, windows=None):
    """Fetch every parameter loop and window, convert each, and concatenate."""
    pd = import_pandas()
    frames = []
    for loop in _param_loops(spec):
        for window_start, window_end in windows or [(None, None)]:
            params = {**base_params, **loop["params"]}
            if window_start or window_end:
                params[spec["range_params"][0]] = window_start
                params[spec["range_params"][1]] = window_end
            raw = _fetch_pages(pro, spec, request_interval, **params)
            frames.append(convert_spec_frame(spec, raw, loop["constants"]))
            if request_interval:
                time.sleep(request_interval)
    if not frames:
        return convert_spec_frame(spec, None)
    frame = pd.concat(frames, ignore_index=True)
    if spec["dedupe_keys"]:
        frame = frame.drop_duplicates(subset=spec["dedupe_keys"], keep="last")
    return frame.sort_values(spec["sort_columns"], kind="stable").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Key sources
# ---------------------------------------------------------------------------


def latest_trading_day(end_date: str | None) -> str:
    end = parse_date_arg(end_date) or datetime.now().date()
    days = read_trading_days(TRADE_CALENDAR_PATH, end - timedelta(days=30), end, "SSE")
    if not days:
        raise ValueError("No trading day found in the local calendar before the requested end date.")
    return days[-1].strftime("%Y%m%d")


def _read_column(path: Path, column: str, filter_column: str | None = None, filter_values=None) -> list[str]:
    pd = import_pandas()
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Missing key source, fetch it first: {path}")
    frame = pd.read_csv(path, dtype=str).fillna("")
    if filter_column:
        frame = frame[frame[filter_column].isin(list(filter_values))]
    return sorted(value for value in frame[column].unique() if value)


def resolve_keys(spec: dict, pro, end_date: str | None) -> list:
    source = spec["keys"]
    if source == "etf_codes":
        return _read_column(TABLE_SPECS["fund_basic"]["csv"], "fund_code", "market", ["E"])
    if source == "ths_index_codes":
        return _read_column(TABLE_SPECS["ths_index"]["csv"], "index_code")
    if source == "futures_contracts":
        return _read_column(FUTURES_BASIC_PATH, "contract_code")
    if source == "global_index_codes":
        # The provider has no index list; the latest day's rows enumerate the codes.
        raw = pro.query(spec["api"], trade_date=latest_trading_day(end_date), fields="ts_code")
        return sorted(raw["ts_code"].dropna().unique()) if raw is not None else []
    if source == "months":
        start = spec["start"] or "200001"
        end = (parse_date_arg(end_date) or datetime.now().date()).strftime("%Y%m")
        months, current = [], date(int(start[:4]), int(start[4:6]), 1)
        while current.strftime("%Y%m") <= end:
            months.append(current.strftime("%Y%m"))
            current = date(current.year + (current.month == 12), current.month % 12 + 1, 1)
        return months
    raise ValueError(f"Unknown key source: {source}")


def _key_request_value(spec: dict, key: str) -> str:
    # Futures member holdings are queried by symbol (IF2609), not the contract code (IF2609.CFX).
    if spec["key_param"] == "symbol":
        return key.split(".")[0]
    return key


def _resolve_params(spec: dict, end_date: str | None) -> dict:
    params = {}
    for name, value in spec["params"].items():
        params[name] = latest_trading_day(end_date) if value == "$latest_trading_day" else value
    return params


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_registered_table(
    name: str,
    token: str,
    start_date: str | None = None,
    end_date: str | None = None,
    update: bool = False,
    refresh_recent_days: int = DEFAULT_REFRESH_RECENT_DAYS,
    stock_kwargs: dict | None = None,
    limit_keys: int | None = None,
    **control,
) -> dict:
    """Fetch one registered table. `control` holds the shared runner flags."""
    spec = TABLE_SPECS[name]
    layout = spec["layout"]
    job_name = f"fetch_{name}"
    start_date = start_date or spec["start"]
    end_date = end_date or datetime.now().strftime("%Y%m%d")
    request_interval = control.get("request_interval", 0.0)
    resume = control.get("resume", False)
    single_control = {key: control[key] for key in ("dry_run", "write_log", "backup_root", "create_backup", "max_retries", "retry_interval") if key in control}
    has_trade_date = "trade_date" in spec["columns"]

    if layout == "single":
        def fetch_fn(pro):
            params = _resolve_params(spec, end_date)
            loops_spec = spec
            if spec["keys"]:
                # Key-driven single tables loop the keys inside one request set.
                keys = resolve_keys(spec, pro, end_date)
                loops_spec = {**spec, "param_loops": [{"params": {spec["key_param"]: _key_request_value(spec, key)}} for key in keys]}
            windows = list(iter_date_windows(start_date, end_date, spec["window_days"])) if spec["window_days"] and start_date else None
            if windows is None and start_date and not spec["keys"] and spec["params"] == {}:
                params = {spec["range_params"][0]: start_date, spec["range_params"][1]: end_date}
            return _fetch_and_convert(pro, loops_spec, request_interval, params, windows)

        return run_single_table_etl(job_name, token, fetch_fn, lambda frame: frame, output_path=spec["csv"], **single_control)

    if layout == "per_stock":
        def fetch_fn(pro, ts_code, stock, stock_start, stock_end):
            params = {spec["key_param"]: ts_code}
            if stock_start or stock_end:
                params[spec["range_params"][0]] = stock_start
                params[spec["range_params"][1]] = stock_end
            return _fetch_pages(pro, spec, request_interval, **params)

        return run_per_stock_etl(
            job_name, token, fetch_fn, lambda raw, stock: convert_spec_frame(spec, raw),
            output_root=spec["csv"], start_date=start_date, end_date=end_date,
            incremental=update and has_trade_date, columns=spec["columns"],
            clip_start_to_list_date=bool(start_date), **(stock_kwargs or {}), **control,
        )

    if layout == "per_date":
        def fetch_fn(pro, day):
            return _fetch_and_convert(pro, spec, request_interval, {spec["date_param"]: day})

        return run_per_date_etl(
            job_name, token, fetch_fn, lambda frame: frame if frame is not None else convert_spec_frame(spec, None),
            output_root=spec["csv"], start_date=start_date, end_date=end_date,
            calendar_days=spec["calendar_days"], **control,
        )

    if layout == "per_period":
        periods = iter_report_periods(start_date, end_date)
        cutoff = (datetime.now() - timedelta(days=refresh_recent_days)).strftime("%Y%m%d")

        def fetch_fn(pro, period):
            return _fetch_and_convert(pro, spec, request_interval, {spec["key_param"]: period})

        return run_per_key_etl(
            job_name, token, keys=periods[:limit_keys], fetch_fn=fetch_fn, convert_fn=lambda frame, period: frame,
            output_path_fn=lambda period: Path(spec["csv"]) / f"{period}.csv",
            resume_skip_fn=lambda period, path: period < cutoff and path.exists() and path.stat().st_size > 0,
            **control,
        )

    if layout == "per_year":
        first_year = parse_date_arg(start_date).year
        last_year = parse_date_arg(end_date).year + spec["end_offset_years"]
        years = [str(year) for year in range(first_year, last_year + 1)]
        current_year = str(datetime.now().year)

        def fetch_fn(pro, year):
            year_start = max(f"{year}0101", start_date)
            year_end = f"{year}1231" if int(year) < int(end_date[:4]) + spec["end_offset_years"] else max(end_date, f"{year}0101")
            if spec["end_offset_years"]:
                year_end = f"{year}1231"
            windows = list(iter_date_windows(year_start, year_end, spec["window_days"] or 366))
            return _fetch_and_convert(pro, spec, request_interval, {}, windows)

        return run_per_key_etl(
            job_name, token, keys=years[:limit_keys], fetch_fn=fetch_fn, convert_fn=lambda frame, year: frame,
            output_path_fn=lambda year: Path(spec["csv"]) / f"{year}.csv",
            # Past years are complete; the current and future years are always re-fetched.
            resume_skip_fn=lambda year, path: year < current_year and path.exists() and path.stat().st_size > 0,
            **{**control, "resume": resume or update},
        )

    if layout == "per_key":
        def fetch_fn(pro, key, incremental_start=None):
            params = {spec["key_param"]: _key_request_value(spec, key)}
            key_start = incremental_start or start_date
            if key_start or end_date:
                params[spec["range_params"][0]] = key_start
                params[spec["range_params"][1]] = end_date
            raw = _fetch_pages(pro, spec, request_interval, **params)
            constants = {spec["key_constant"]: key} if spec["key_constant"] else None
            return convert_spec_frame(spec, raw, constants)

        return run_per_key_etl(
            job_name, token,
            keys=lambda pro: resolve_keys(spec, pro, end_date)[:limit_keys],
            fetch_fn=fetch_fn, convert_fn=lambda frame, key: frame,
            output_path_fn=lambda key: Path(spec["csv"]) / f"{key}.csv",
            incremental=update and has_trade_date, columns=spec["columns"],
            merge_keys=spec["dedupe_keys"] or spec["sort_columns"], date_column="trade_date",
            **control,
        )

    raise ValueError(f"Unsupported layout {layout} for table {name}")
