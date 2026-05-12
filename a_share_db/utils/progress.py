"""Reusable progress reporting helpers for long-running command-line jobs."""

from __future__ import annotations

import sys
import time
from typing import TextIO


def format_duration(seconds: float) -> str:
    """Format a duration for compact terminal progress output."""
    seconds = max(int(seconds), 0)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h{minutes:02d}m{seconds:02d}s"
    if minutes:
        return f"{minutes}m{seconds:02d}s"
    return f"{seconds}s"


class ProgressReporter:
    """Print elapsed time and ETA for long-running stock loops."""

    def __init__(
        self,
        total: int,
        every: int = 50,
        label: str = "Progress",
        stream: TextIO | None = None,
    ) -> None:
        self.total = total
        self.every = every
        self.label = label
        self.stream = stream or sys.stdout
        self.started_at = time.time()

    @property
    def enabled(self) -> bool:
        return self.every > 0 and self.total > 0

    def maybe_print(
        self,
        current: int,
        row_count: int = 0,
        skipped_count: int = 0,
        failure_count: int = 0,
        extra: str = "",
    ) -> None:
        if not self.enabled:
            return
        # Print first, every N items, and final item so long jobs show movement.
        if current != 1 and current % self.every != 0 and current != self.total:
            return
        self.print(
            current=current,
            row_count=row_count,
            skipped_count=skipped_count,
            failure_count=failure_count,
            extra=extra,
        )

    def print(
        self,
        current: int,
        row_count: int = 0,
        skipped_count: int = 0,
        failure_count: int = 0,
        extra: str = "",
    ) -> None:
        if self.total <= 0:
            return
        elapsed = time.time() - self.started_at
        # ETA is based on observed average speed, so it becomes steadier over time.
        rate = current / elapsed if elapsed > 0 else 0
        remaining = (self.total - current) / rate if rate > 0 else 0
        percent = current / self.total * 100
        message = (
            f"{self.label} {current}/{self.total} ({percent:.1f}%) "
            f"elapsed={format_duration(elapsed)} eta={format_duration(remaining)} "
            f"rows={row_count} skipped={skipped_count} failed={failure_count}"
        )
        if extra:
            message = f"{message} {extra}"
        print(message, file=self.stream, flush=True)
