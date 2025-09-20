"""Utility helpers for working with output directories."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

TimestampStr = str


def current_timestamp_str() -> TimestampStr:
    """Return the current timestamp as ``YYYYMMDDHHMMSS`` in the local timezone."""

    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d%H%M%S")


def resolve_timestamped_output_dir(base: Path) -> Path:
    """Append a timestamped leaf directory to *base* and create it."""

    concrete = base / current_timestamp_str()
    concrete.mkdir(parents=True, exist_ok=False)
    return concrete


__all__ = ["current_timestamp_str", "resolve_timestamped_output_dir"]
