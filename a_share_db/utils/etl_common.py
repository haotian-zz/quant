"""Shared ETL helpers for Tushare-backed fetch scripts.

The first generation of scripts copied these helpers into every command file.
New tables should import from here so file writing, logging, stock selection,
retry and pagination behave the same way across the warehouse.
"""

from __future__ import annotations

import csv
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable, Iterable, Iterator

from a_share_db.constant.paths import build_data_backup_path


ETL_LOG_FIELDS = [
    "job_name",
    "source",
    "start_time",
    "end_time",
    "status",
    "row_count",
    "error_message",
]

# Tushare pagination: most interfaces accept offset/limit and return at most
# one page per call. Page size is kept below common provider caps.
DEFAULT_PAGE_SIZE = 4000
MAX_PAGES_PER_REQUEST = 200


def import_pandas():
    try:
        import pandas as pd
    except ImportError as exc:
        raise SystemExit("Missing dependency. Install with: python -m pip install pandas") from exc
    return pd


def import_tushare():
    try:
        import tushare as ts
    except ImportError as exc:
        raise SystemExit("Missing dependency. Install with: python -m pip install tushare") from exc
    return ts


_PRO_CACHE: dict[str, object] = {}


def get_tushare_pro(token: str):
    """Return a cached Tushare pro client so loops do not rebuild it per request."""
    if not token:
        raise ValueError("Tushare token is required.")
    client = _PRO_CACHE.get(token)
    if client is None:
        ts = import_tushare()
        ts.set_token(token)
        client = ts.pro_api(token)
        _PRO_CACHE[token] = client
    return client


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def format_tushare_date(value) -> str:
    """Convert provider YYYYMMDD values into local ISO dates; blanks stay blank."""
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text.lower() in {"nan", "nat", "none"}:
        return ""
    if text.endswith(".0"):
        text = text[:-2]
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    return text


def format_tushare_datetime(value) -> str:
    """Normalize provider timestamps into local YYYY-MM-DD HH:MM:SS text."""
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text.lower() in {"nan", "nat", "none"}:
        return ""
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y%m%d %H:%M:%S", "%Y%m%d%H%M%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, pattern).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return text


def parse_date_arg(value: str | None) -> date | None:
    """Accept YYYYMMDD or YYYY-MM-DD at the CLI boundary."""
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) == 8 and text.isdigit():
        return datetime.strptime(text, "%Y%m%d").date()
    return datetime.strptime(text, "%Y-%m-%d").date()


def provider_date(value: date | str | None) -> str | None:
    """Provider APIs use compact YYYYMMDD dates."""
    if value is None or value == "":
        return None
    if isinstance(value, str):
        value = parse_date_arg(value)
    return value.strftime("%Y%m%d")


def local_date(value: date | None) -> str:
    return value.strftime("%Y-%m-%d") if value else ""


def ts_code_to_code(series):
    """Strip the provider exchange suffix so formal tables keep six-digit codes."""
    return series.fillna("").astype(str).str.strip().str.split(".").str[0].str.zfill(6)


def ensure_columns(frame, columns: Iterable[str]):
    """Fill provider columns that were omitted so conversion stays simple."""
    pd = import_pandas()
    columns = list(columns)
    if frame is None:
        return pd.DataFrame(columns=columns)
    for column in columns:
        if column not in frame.columns:
            frame[column] = None
    return frame[columns]


def scale_numeric(series, factor: float):
    """Convert provider units (for example 万股 or 千元) into local units."""
    pd = import_pandas()
    return pd.to_numeric(series, errors="coerce") * factor


def clean_formal_frame(output, columns: list[str], sort_columns: list[str], code_column: str | None = "code"):
    """Order columns, drop malformed key rows, and sort for stable formal files."""
    output = output[columns]
    if code_column and code_column in output.columns:
        output = output[output[code_column].astype(str).str.fullmatch(r"\d{6}", na=False)]
    # Only the primary time key is mandatory; secondary dates (out_date, pay_date, ...) may be blank.
    primary_date = next((column for column in sort_columns if column.endswith(("date", "period")) and column in output.columns), None)
    if primary_date:
        output = output[output[primary_date].astype(str).str.fullmatch(r"\d{4}-\d{2}-\d{2}", na=False)]
    return output.sort_values(sort_columns, kind="stable").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Stock selection
# ---------------------------------------------------------------------------

DEFAULT_STOCK_STATUSES = ["listed"]


def read_stock_basic(path: Path, statuses: Iterable[str] | None = DEFAULT_STOCK_STATUSES):
    """Load the local stock master and optionally filter by local status values."""
    pd = import_pandas()
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Missing stock_basic file: {path}")
    frame = pd.read_csv(path, dtype=str).fillna("")
    required = {"code", "exchange"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"stock_basic missing columns: {', '.join(sorted(missing))}")
    statuses = [status for status in (statuses or []) if status]
    if statuses and "status" in frame.columns and "all" not in statuses:
        frame = frame[frame["status"].isin(statuses)]
    return frame


def load_requested_codes(codes: Iterable[str] | None, codes_file: Path | None) -> list[str]:
    selected = []
    if codes:
        selected.extend(codes)
    if codes_file:
        selected.extend(
            line.strip()
            for line in Path(codes_file).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        )

    normalized = []
    seen = set()
    for code in selected:
        value = str(code).strip().split(".")[0].zfill(6)
        if value and value not in seen:
            # Keep input order but remove duplicate codes.
            normalized.append(value)
            seen.add(value)
    return normalized


def select_stock_rows(stock_basic, codes: list[str], all_stocks: bool, limit_stocks: int | None):
    if not codes and not all_stocks:
        raise ValueError("Pass --codes, --codes-file, or --all-stocks.")
    if codes:
        selected = stock_basic[stock_basic["code"].isin(codes)].copy()
        found = set(selected["code"])
        missing = [code for code in codes if code not in found]
        if missing:
            raise ValueError("Codes not found in stock_basic.csv: " + ", ".join(missing))
        # Preserve explicit caller order for small targeted runs.
        selected["__order"] = selected["code"].map({code: index for index, code in enumerate(codes)})
        selected = selected.sort_values("__order", kind="stable").drop(columns=["__order"])
    else:
        # Full-market jobs use a stable exchange/code order for repeatable progress.
        selected = stock_basic.sort_values(["exchange", "code"], kind="stable").copy()

    if limit_stocks is not None:
        if limit_stocks < 0:
            raise ValueError("limit-stocks must be greater than or equal to 0.")
        selected = selected.head(limit_stocks)
    return selected


# ---------------------------------------------------------------------------
# Trade calendar helpers
# ---------------------------------------------------------------------------


def read_trading_days(
    path: Path,
    start_date: date | None,
    end_date: date | None,
    exchange: str = "SSE",
) -> list[date]:
    """Return trading days from the local calendar for one exchange."""
    pd = import_pandas()
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Missing trade_calendar file: {path}")
    frame = pd.read_csv(path, dtype=str).fillna("")
    frame = frame[frame["exchange"].str.upper().eq(exchange.upper())]
    frame = frame[frame["is_trading_day"].astype(str).isin({"1", "1.0", "True", "true"})]
    days = []
    for text in sorted(frame["calendar_date"].unique()):
        try:
            value = datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError:
            continue
        if start_date and value < start_date:
            continue
        if end_date and value > end_date:
            continue
        days.append(value)
    return days


def iter_date_windows(
    start_date: str | None,
    end_date: str | None,
    window_days: int,
) -> Iterator[tuple[str | None, str | None]]:
    """Split a provider date range into calendar-day windows below row caps."""
    if not start_date or not end_date:
        yield provider_date(start_date), provider_date(end_date)
        return
    start = parse_date_arg(start_date)
    end = parse_date_arg(end_date)
    if start > end:
        raise ValueError("start-date must be earlier than or equal to end-date.")
    current = start
    while current <= end:
        window_end = min(current + timedelta(days=window_days - 1), end)
        yield current.strftime("%Y%m%d"), window_end.strftime("%Y%m%d")
        current = window_end + timedelta(days=1)


def iter_report_periods(start_date: str | None, end_date: str | None) -> list[str]:
    """Return quarterly report periods (YYYYMMDD) covering the requested range."""
    start = parse_date_arg(start_date) or date(1990, 1, 1)
    end = parse_date_arg(end_date) or datetime.now().date()
    periods = []
    for year in range(start.year, end.year + 1):
        for month_day in ("0331", "0630", "0930", "1231"):
            period = date(year, int(month_day[:2]), int(month_day[2:]))
            if start <= period <= end:
                periods.append(period.strftime("%Y%m%d"))
    return periods


# ---------------------------------------------------------------------------
# Provider request helpers
# ---------------------------------------------------------------------------


def retry_call(func: Callable, max_retries: int, retry_interval: float):
    """Retry transient provider or network failures before giving up."""
    if max_retries < 1:
        raise ValueError("max-retries must be greater than or equal to 1.")
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            return func()
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                time.sleep(retry_interval)
    raise last_error


def fetch_paginated(
    pro,
    api_name: str,
    fields: Iterable[str],
    page_size: int = DEFAULT_PAGE_SIZE,
    request_interval: float = 0.0,
    **params,
):
    """Fetch every page of a Tushare query using offset/limit pagination.

    Provider row caps differ per interface, so callers pass a page size that is
    safely below the cap for that interface. The loop stops on a short page.
    """
    pd = import_pandas()
    fields = list(fields)
    frames = []
    offset = 0
    for _ in range(MAX_PAGES_PER_REQUEST):
        frame = pro.query(
            api_name,
            fields=",".join(fields),
            limit=page_size,
            offset=offset,
            **{key: value for key, value in params.items() if value not in (None, "")},
        )
        if frame is None or frame.empty:
            break
        frames.append(ensure_columns(frame, fields))
        if len(frame) < page_size:
            break
        offset += page_size
        if request_interval:
            time.sleep(request_interval)
    if not frames:
        return pd.DataFrame(columns=fields)
    return pd.concat(frames, ignore_index=True)


# ---------------------------------------------------------------------------
# File and log helpers
# ---------------------------------------------------------------------------


def build_backup_timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def write_csv(
    frame,
    path: Path,
    backup_root: Path,
    backup_timestamp: str | None = None,
    create_backup: bool = False,
) -> Path | None:
    """Write a CSV atomically; optional backup moves the previous file first."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temp_path, index=False, encoding="utf-8", lineterminator="\n")
    backup_path = None

    if create_backup and path.exists():
        backup_timestamp = backup_timestamp or build_backup_timestamp()
        backup_path = build_data_backup_path(path, Path(backup_root), backup_timestamp)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        path.replace(backup_path)

    try:
        temp_path.replace(path)
    except Exception:
        # Restore the previous file if replacement fails after the backup move.
        if backup_path and backup_path.exists() and not path.exists():
            backup_path.replace(path)
        raise
    return backup_path


def read_existing_csv(path: Path, columns: list[str], string_columns: Iterable[str] = ("code",)):
    """Read a formal CSV as an empty-safe frame with the expected columns."""
    pd = import_pandas()
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=columns)
    dtype = {column: str for column in string_columns}
    frame = pd.read_csv(path, dtype=dtype)
    return ensure_columns(frame, columns)


def merge_rows(existing, new_rows, columns: list[str], keys: list[str]):
    """Union two formal frames, keeping the latest row for duplicate keys."""
    pd = import_pandas()
    if existing is None or existing.empty:
        merged = new_rows.copy()
    elif new_rows is None or new_rows.empty:
        merged = existing.copy()
    else:
        merged = pd.concat([existing, new_rows], ignore_index=True)
    merged = ensure_columns(merged, columns)
    if not merged.empty:
        if "code" in merged.columns:
            merged["code"] = merged["code"].astype(str).str.zfill(6)
        merged = merged.drop_duplicates(subset=keys, keep="last")
        merged = merged.sort_values(keys, kind="stable")
    return merged.reset_index(drop=True)


def append_etl_log(
    log_path: Path,
    job_name: str,
    source: str,
    start_time: str,
    end_time: str,
    status: str,
    row_count: int,
    error_message: str,
) -> None:
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    exists = log_path.exists()
    with log_path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=ETL_LOG_FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow(
            {
                "job_name": job_name,
                "source": source,
                "start_time": start_time,
                "end_time": end_time,
                "status": status,
                "row_count": row_count,
                "error_message": error_message,
            }
        )


def summarize_failures(failures: list[dict], key: str = "item", limit: int = 20) -> str:
    """Keep log messages bounded even when many items fail."""
    if not failures:
        return ""
    message = "; ".join(f"{item.get(key, '')}: {item.get('error', '')}" for item in failures[:limit])
    if len(failures) > limit:
        message += f"; ... {len(failures) - limit} more"
    return message


def convert_mapped_frame(
    raw,
    field_map: dict[str, str],
    columns: list[str],
    sort_columns: list[str],
    date_columns: Iterable[str] = (),
    datetime_columns: Iterable[str] = (),
    scales: dict[str, float] | None = None,
    value_maps: dict[str, dict] | None = None,
    code_fields: Iterable[str] = ("ts_code",),
    code_column: str | None = "code",
    constants: dict[str, object] | None = None,
):
    """Convert a raw provider frame into a formal frame using a field mapping.

    field_map is ordered provider_field -> local_column. Provider security
    codes are stripped to six digits, provider dates become ISO dates, scaled
    fields are multiplied into local units, and mapped fields are translated
    through value_maps. Constants add local columns that have no provider field.
    """
    pd = import_pandas()
    raw = ensure_columns(raw, field_map.keys())
    date_columns = set(date_columns)
    datetime_columns = set(datetime_columns)
    scales = scales or {}
    value_maps = value_maps or {}
    code_fields = set(code_fields)
    # Build all columns first and assemble once; wide statements have 150+ fields.
    converted: dict[str, object] = {}
    for provider_field, local_column in field_map.items():
        series = raw[provider_field]
        if provider_field in code_fields:
            converted[local_column] = ts_code_to_code(series)
        elif local_column in date_columns:
            converted[local_column] = series.map(format_tushare_date)
        elif local_column in datetime_columns:
            converted[local_column] = series.map(format_tushare_datetime)
        elif provider_field in scales:
            converted[local_column] = scale_numeric(series, scales[provider_field])
        elif provider_field in value_maps:
            text = series.fillna("").astype(str).str.strip()
            converted[local_column] = text.map(value_maps[provider_field]).fillna(text)
        else:
            converted[local_column] = series
    for column, value in (constants or {}).items():
        converted[column] = value
    converted["update_time"] = now_text()
    output = pd.DataFrame(converted, index=raw.index)
    return clean_formal_frame(output, columns, sort_columns, code_column=code_column)
