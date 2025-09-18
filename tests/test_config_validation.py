"""Tests for configuration loading and validation."""

from __future__ import annotations

from pathlib import Path

from saber.config_loader import load_tournament_config
from saber.detectors import detect_config_issues


def test_full_tournament_config_is_valid() -> None:
    """The full sample tournament should validate cleanly."""
    path = Path("config/tournaments/full_3x3.yaml")
    config = load_tournament_config(path)
    assert config["name"] == "Full 3x3 Tournament"
    assert detect_config_issues(config) == []
