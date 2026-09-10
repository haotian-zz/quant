"""Generic ETL loops shared by the second-generation fetch scripts.

Three layouts cover every new table:

- per-stock:  one formal CSV per stock, driven by stock_basic (resume per file)
- per-date:   provider queried by trade_date, formal CSV written per year
- single:     one formal CSV for the whole table (metadata, macro, summaries)

Scripts only provide fetch/convert callables plus paths; retries, progress,
resume, atomic writes and ETL logging live here.
"""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable, Iterable

from a_share_db.constant.commands import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_PROGRESS_EVERY,
    DEFAULT_REQUEST_INTERVAL,
    DEFAULT_RETRY_INTERVAL,
)
from a_share_db.constant.paths import BACKUP_ROOT, ETL_LOG_PATH, STOCK_BASIC_PATH, TRADE_CALENDAR_PATH
from a_share_db.utils.etl_common import (
    DEFAULT_STOCK_STATUSES,
    append_etl_log,
    build_backup_timestamp,
    get_tushare_pro,
    import_pandas,
    load_requested_codes,
    merge_rows,
    now_text,
    parse_date_arg,
    read_existing_csv,
    read_stock_basic,
    read_trading_days,
    retry_call,
    select_stock_rows,
    summarize_failures,
    write_csv,
)
from a_share_db.utils.progress import ProgressReporter
from a_share_db.utils.provider_codes import build_tushare_ts_code


TUSHARE_SOURCE = "tushare"


def _validate_intervals(request_interval: float, retry_interval: float) -> None:
    if request_interval < 0:
        raise ValueError("request-interval must be greater than or equal to 0.")
    if retry_interval < 0:
        raise ValueError("retry-interval must be greater than or equal to 0.")


def _file_is_complete(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


class EtlRun:
    """Track counters and write the ETL log row when a job finishes."""

    def __init__(self, job_name: str, log_path: Path, write_log: bool, dry_run: bool, backup_root: Path):
        self.job_name = job_name
        self.log_path = Path(log_path)
        self.write_log = write_log and not dry_run
        self.dry_run = dry_run
        self.backup_root = Path(backup_root)
        self.backup_timestamp = build_backup_timestamp()
        self.start_time = now_text()
        self.row_count = 0
        self.skipped_count = 0
        self.failures: list[dict] = []
        self.backup_paths: list[str] = []
        self.status = "failed"
        self.error_message = ""

    def write(self, frame, path: Path, create_backup: bool) -> None:
        if self.dry_run:
            return
        backup_path = write_csv(
            frame,
            Path(path),
            backup_root=self.backup_root,
            backup_timestamp=self.backup_timestamp,
            create_backup=create_backup,
        )
        if backup_path:
            self.backup_paths.append(str(backup_path))

    def finish(self, failure_key: str = "item") -> None:
        self.status = "partial" if self.failures else "success"
        self.error_message = summarize_failures(self.failures, key=failure_key)

    def fail(self, exc: Exception) -> None:
        self.status = "failed"
        self.error_message = str(exc)

    def log(self) -> None:
        if self.write_log:
            append_etl_log(
                self.log_path,
                job_name=self.job_name,
                source=TUSHARE_SOURCE,
                start_time=self.start_time,
                end_time=now_text(),
                status=self.status,
                row_count=self.row_count,
                error_message=self.error_message,
            )

    def result(self, **extra) -> dict:
        payload = {
            "status": self.status,
            "row_count": self.row_count,
            "skipped_count": self.skipped_count,
            "failure_count": len(self.failures),
            "failures": self.failures,
            "error_message": self.error_message,
            "dry_run": self.dry_run,
            "backup_paths": self.backup_paths,
        }
        payload.update(extra)
        return payload


def run_per_stock_etl(
    job_name: str,
    token: str,
    fetch_fn: Callable,
    convert_fn: Callable,
    output_root: Path,
    codes: Iterable[str] | None = None,
    codes_file: Path | None = None,
    all_stocks: bool = False,
    stock_basic_path: Path = STOCK_BASIC_PATH,
    statuses: Iterable[str] = DEFAULT_STOCK_STATUSES,
    start_date: str | None = None,
    end_date: str | None = None,
    raw_output_root: Path | None = None,
    write_raw: bool = False,
    limit_stocks: int | None = None,
    dry_run: bool = False,
    resume: bool = False,
    write_log: bool = True,
    log_path: Path = ETL_LOG_PATH,
    backup_root: Path = BACKUP_ROOT,
    create_backup: bool = False,
    request_interval: float = DEFAULT_REQUEST_INTERVAL,
    progress_every: int = DEFAULT_PROGRESS_EVERY,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_interval: float = DEFAULT_RETRY_INTERVAL,
    stop_on_error: bool = False,
    clip_start_to_list_date: bool = True,
    progress_label: str | None = None,
    incremental: bool = False,
    columns: list[str] | None = None,
    merge_keys: tuple[str, ...] = ("code", "trade_date"),
) -> dict:
    """Fetch one provider table per stock and write data/.../{code}.csv files.

    fetch_fn(pro, ts_code, stock_row, start_date, end_date) -> raw DataFrame
    convert_fn(raw, stock_row) -> formal DataFrame

    With incremental=True an existing file is the checkpoint: rows are fetched
    from max(trade_date)+1, merged on merge_keys and the file is rewritten only
    when new rows arrived. Missing files are fetched in full.
    """
    if not token:
        raise ValueError("Tushare token is required.")
    run = EtlRun(job_name, log_path, write_log, dry_run, backup_root)
    stock_count = 0
    try:
        _validate_intervals(request_interval, retry_interval)
        pro = get_tushare_pro(token)
        stock_basic = read_stock_basic(Path(stock_basic_path), statuses)
        selected_codes = load_requested_codes(codes, codes_file)
        stocks = select_stock_rows(stock_basic, selected_codes, all_stocks, limit_stocks)
        stock_count = len(stocks)
        progress = ProgressReporter(stock_count, every=progress_every, label=progress_label or f"Fetch {job_name}")
        requested_start = parse_date_arg(start_date)

        for index, stock in enumerate(stocks.to_dict("records"), start=1):
            code = stock["code"]
            output_path = Path(output_root) / f"{code}.csv"
            ts_code = ""
            try:
                existing = None
                if incremental and columns and _file_is_complete(output_path):
                    existing = read_existing_csv(output_path, columns)
                elif resume and _file_is_complete(output_path):
                    run.skipped_count += 1
                    continue

                ts_code = build_tushare_ts_code(code, stock.get("exchange", ""))
                stock_start = start_date
                if clip_start_to_list_date and requested_start is not None:
                    # Do not waste requests on the window before a stock was listed.
                    list_date = parse_date_arg(stock.get("list_date") or None)
                    if list_date and list_date > requested_start:
                        stock_start = list_date.strftime("%Y%m%d")
                if existing is not None and not existing.empty:
                    # Continue from the day after the local file ends.
                    local_max = existing["trade_date"].dropna().astype(str).max()
                    next_day = parse_date_arg(local_max) + timedelta(days=1)
                    if requested_start is None or next_day > requested_start:
                        stock_start = next_day.strftime("%Y%m%d")
                    requested_end = parse_date_arg(end_date)
                    if requested_end is not None and next_day > requested_end:
                        run.skipped_count += 1
                        continue

                raw = retry_call(
                    lambda: fetch_fn(pro, ts_code, stock, stock_start, end_date),
                    max_retries=max_retries,
                    retry_interval=retry_interval,
                )
                normalized = convert_fn(raw, stock)
                run.row_count += len(normalized)
                if existing is not None:
                    merged = merge_rows(existing, normalized, columns, list(merge_keys))
                    if len(merged) > len(existing):
                        run.write(merged, output_path, create_backup)
                    else:
                        run.skipped_count += 1
                else:
                    run.write(normalized, output_path, create_backup)
                if write_raw and raw_output_root is not None and not raw.empty:
                    run.write(raw, Path(raw_output_root) / f"{code}.csv", create_backup)
                if request_interval:
                    time.sleep(request_interval)
            except Exception as exc:
                # Keep long all-stock jobs running unless the caller wants fail-fast.
                run.failures.append({"item": f"{code}({ts_code})", "code": code, "ts_code": ts_code, "error": str(exc)})
                if stop_on_error:
                    raise
            finally:
                progress.maybe_print(
                    index,
                    row_count=run.row_count,
                    skipped_count=run.skipped_count,
                    failure_count=len(run.failures),
                )

        run.finish()
        return run.result(stock_count=stock_count, output_root=str(output_root))
    except Exception as exc:
        run.fail(exc)
        raise
    finally:
        run.log()


def run_per_date_etl(
    job_name: str,
    token: str,
    fetch_fn: Callable,
    convert_fn: Callable,
    output_root: Path,
    start_date: str | None,
    end_date: str | None,
    trade_calendar_path: Path = TRADE_CALENDAR_PATH,
    calendar_exchange: str = "SSE",
    raw_output_root: Path | None = None,
    write_raw: bool = False,
    limit_days: int | None = None,
    dry_run: bool = False,
    resume: bool = False,
    write_log: bool = True,
    log_path: Path = ETL_LOG_PATH,
    backup_root: Path = BACKUP_ROOT,
    create_backup: bool = False,
    request_interval: float = DEFAULT_REQUEST_INTERVAL,
    progress_every: int = DEFAULT_PROGRESS_EVERY,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_interval: float = DEFAULT_RETRY_INTERVAL,
    stop_on_error: bool = False,
    progress_label: str | None = None,
) -> dict:
    """Fetch a provider table by trade_date and write data/.../{year}.csv files.

    fetch_fn(pro, trade_date_yyyymmdd) -> raw DataFrame
    convert_fn(raw) -> formal DataFrame

    Yearly files are written once a year's trading days are all fetched, so a
    resumed run re-fetches only the year that was interrupted. The last year
    of the requested range is always re-fetched because it may be incomplete.
    """
    if not token:
        raise ValueError("Tushare token is required.")
    run = EtlRun(job_name, log_path, write_log, dry_run, backup_root)
    pd = import_pandas()
    day_count = 0
    year_count = 0
    try:
        _validate_intervals(request_interval, retry_interval)
        pro = get_tushare_pro(token)
        requested_start = parse_date_arg(start_date)
        requested_end = parse_date_arg(end_date) or datetime.now().date()
        if requested_start is None:
            raise ValueError("start-date is required for per-date fetches.")
        days = read_trading_days(Path(trade_calendar_path), requested_start, requested_end, calendar_exchange)
        if limit_days is not None:
            if limit_days < 0:
                raise ValueError("limit-days must be greater than or equal to 0.")
            days = days[:limit_days]
        days_by_year: dict[int, list[date]] = defaultdict(list)
        for day in days:
            days_by_year[day.year].append(day)
        last_year = max(days_by_year) if days_by_year else None

        # Resume works at year granularity: a finished year file is skipped
        # unless it is the final year, which may still be growing.
        pending_years = []
        for year in sorted(days_by_year):
            year_path = Path(output_root) / f"{year}.csv"
            if resume and year != last_year and _file_is_complete(year_path):
                run.skipped_count += len(days_by_year[year])
                continue
            pending_years.append(year)

        day_count = sum(len(days_by_year[year]) for year in pending_years)
        progress = ProgressReporter(day_count, every=progress_every, label=progress_label or f"Fetch {job_name}")
        index = 0
        for year in pending_years:
            year_frames = []
            raw_frames = []
            for day in days_by_year[year]:
                index += 1
                day_text = day.strftime("%Y%m%d")
                try:
                    raw = retry_call(
                        lambda: fetch_fn(pro, day_text),
                        max_retries=max_retries,
                        retry_interval=retry_interval,
                    )
                    normalized = convert_fn(raw)
                    run.row_count += len(normalized)
                    if not normalized.empty:
                        year_frames.append(normalized)
                    if write_raw and raw is not None and not raw.empty:
                        raw_frames.append(raw)
                    if request_interval:
                        time.sleep(request_interval)
                except Exception as exc:
                    run.failures.append({"item": day.isoformat(), "trade_date": day.isoformat(), "error": str(exc)})
                    if stop_on_error:
                        raise
                finally:
                    progress.maybe_print(
                        index,
                        row_count=run.row_count,
                        skipped_count=run.skipped_count,
                        failure_count=len(run.failures),
                        extra=f"year={year}",
                    )

            # A year with failed days is still written so partial data is usable;
            # rerun without --resume for that year to fill the gaps.
            year_frame = pd.concat(year_frames, ignore_index=True) if year_frames else convert_fn(None)
            run.write(year_frame, Path(output_root) / f"{year}.csv", create_backup)
            if write_raw and raw_output_root is not None and raw_frames:
                run.write(pd.concat(raw_frames, ignore_index=True), Path(raw_output_root) / f"{year}.csv", create_backup)
            year_count += 1

        run.finish()
        return run.result(day_count=day_count, year_count=year_count, output_root=str(output_root))
    except Exception as exc:
        run.fail(exc)
        raise
    finally:
        run.log()


def run_single_table_etl(
    job_name: str,
    token: str,
    fetch_fn: Callable,
    convert_fn: Callable,
    output_path: Path,
    raw_output_path: Path | None = None,
    write_raw: bool = False,
    limit: int | None = None,
    dry_run: bool = False,
    write_log: bool = True,
    log_path: Path = ETL_LOG_PATH,
    backup_root: Path = BACKUP_ROOT,
    create_backup: bool = False,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_interval: float = DEFAULT_RETRY_INTERVAL,
) -> dict:
    """Fetch a whole table in one logical request and write one formal CSV.

    fetch_fn(pro) -> raw DataFrame
    convert_fn(raw) -> formal DataFrame
    """
    if not token:
        raise ValueError("Tushare token is required.")
    run = EtlRun(job_name, log_path, write_log, dry_run, backup_root)
    total_row_count = 0
    try:
        if retry_interval < 0:
            raise ValueError("retry-interval must be greater than or equal to 0.")
        pro = get_tushare_pro(token)
        raw = retry_call(lambda: fetch_fn(pro), max_retries=max_retries, retry_interval=retry_interval)
        normalized = convert_fn(raw)
        total_row_count = len(normalized)
        if limit is not None:
            if limit < 0:
                raise ValueError("limit must be greater than or equal to 0.")
            # Limit only trims the local sample after the full conversion ran.
            normalized = normalized.head(limit)
            raw = raw.head(limit)
        run.row_count = len(normalized)
        run.write(normalized, Path(output_path), create_backup)
        if write_raw and raw_output_path is not None:
            run.write(raw, Path(raw_output_path), create_backup)
        run.finish()
        return run.result(total_row_count=total_row_count, output=str(output_path))
    except Exception as exc:
        run.fail(exc)
        raise
    finally:
        run.log()


def run_per_key_etl(
    job_name: str,
    token: str,
    keys: Iterable,
    fetch_fn: Callable,
    convert_fn: Callable,
    output_path_fn: Callable,
    raw_output_path_fn: Callable | None = None,
    write_raw: bool = False,
    dry_run: bool = False,
    resume: bool = False,
    resume_skip_fn: Callable | None = None,
    write_log: bool = True,
    log_path: Path = ETL_LOG_PATH,
    backup_root: Path = BACKUP_ROOT,
    create_backup: bool = False,
    request_interval: float = DEFAULT_REQUEST_INTERVAL,
    progress_every: int = DEFAULT_PROGRESS_EVERY,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_interval: float = DEFAULT_RETRY_INTERVAL,
    stop_on_error: bool = False,
    progress_label: str | None = None,
) -> dict:
    """Fetch one file per arbitrary key (index code, report period, ...).

    fetch_fn(pro, key) -> raw DataFrame
    convert_fn(raw, key) -> formal DataFrame
    output_path_fn(key) -> Path
    resume_skip_fn(key, path) -> bool, optional override of the resume rule
    """
    if not token:
        raise ValueError("Tushare token is required.")
    run = EtlRun(job_name, log_path, write_log, dry_run, backup_root)
    keys = list(keys)
    try:
        _validate_intervals(request_interval, retry_interval)
        pro = get_tushare_pro(token)
        progress = ProgressReporter(len(keys), every=progress_every, label=progress_label or f"Fetch {job_name}")
        for index, key in enumerate(keys, start=1):
            output_path = Path(output_path_fn(key))
            try:
                skip = resume_skip_fn(key, output_path) if resume_skip_fn else _file_is_complete(output_path)
                if resume and skip:
                    run.skipped_count += 1
                    continue
                raw = retry_call(lambda: fetch_fn(pro, key), max_retries=max_retries, retry_interval=retry_interval)
                normalized = convert_fn(raw, key)
                run.row_count += len(normalized)
                run.write(normalized, output_path, create_backup)
                if write_raw and raw_output_path_fn is not None and not raw.empty:
                    run.write(raw, Path(raw_output_path_fn(key)), create_backup)
                if request_interval:
                    time.sleep(request_interval)
            except Exception as exc:
                run.failures.append({"item": str(key), "key": str(key), "error": str(exc)})
                if stop_on_error:
                    raise
            finally:
                progress.maybe_print(
                    index,
                    row_count=run.row_count,
                    skipped_count=run.skipped_count,
                    failure_count=len(run.failures),
                )
        run.finish()
        return run.result(key_count=len(keys))
    except Exception as exc:
        run.fail(exc)
        raise
    finally:
        run.log()
