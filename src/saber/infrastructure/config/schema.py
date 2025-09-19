"""Schema utilities for configuration validation."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

import yaml

SCHEMA_FILE = Path(__file__).resolve().parent / "schemas" / "config-schema.json"


def load_schema() -> Mapping[str, object]:
    schema_text = SCHEMA_FILE.read_text(encoding="utf-8")
    return yaml.safe_load(schema_text)


__all__ = ["load_schema", "SCHEMA_FILE"]
