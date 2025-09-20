"""Tests for timestamped output directory helpers."""

from __future__ import annotations

from pathlib import Path

import re
import time

from saber.utils import paths


def test_resolve_timestamped_output_dir_creates_directory(monkeypatch, tmp_path):
    base = tmp_path / "results" / "test"
    monkeypatch.setattr(paths, "current_timestamp_str", lambda: "20250101120000")
    resolved = paths.resolve_timestamped_output_dir(base)
    assert resolved.exists()
    assert resolved.name == "20250101120000"


def test_resolve_timestamped_output_dir_unique(monkeypatch, tmp_path):
    base = tmp_path / "results" / "test"
    monkeypatch.setattr(paths, "current_timestamp_str", lambda: "20250101120000")
    first = paths.resolve_timestamped_output_dir(base)
    monkeypatch.setattr(paths, "current_timestamp_str", lambda: "20250101120001")
    second = paths.resolve_timestamped_output_dir(base)
    assert first != second
    assert second.exists()


def test_current_timestamp_str_format(monkeypatch):
    class FixedDatetime(paths.datetime):  # type: ignore[attr-defined]
        @classmethod
        def now(cls, tz=None):
            return cls(2025, 1, 2, 3, 4, 5, tzinfo=paths.timezone.utc)

    monkeypatch.setattr(paths, "datetime", FixedDatetime)
    ts = paths.current_timestamp_str()
    assert re.fullmatch(r"\d{14}", ts)
    assert ts == "20250102030405"
