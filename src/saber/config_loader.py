"""Utilities for loading and validating Saber configuration files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, TypedDict, cast

import yaml
from jsonschema import Draft202012Validator

SCHEMA_FILE = Path(__file__).resolve().parent / "schemas" / "config-schema.json"


class TournamentSettings(TypedDict):
    """Settings applied to every tournament match."""

    max_turns: int
    repetitions: int
    output_dir: str
    privacy_tier: str


class TournamentConfig(TypedDict):
    """Top-level tournament configuration structure."""

    name: str
    description: str
    models: list[str]
    exploits: list[str]
    settings: TournamentSettings


@dataclass(frozen=True)
class ValidationMessage:
    """Container for schema validation output."""

    path: str
    message: str


def _read_yaml(path: Path) -> Any:
    """Load YAML document from *path* and return the parsed object."""
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if data is None:
        raise ValueError(f"Config at '{path}' is empty.")
    return data


def _load_schema(schema_path: Path) -> Mapping[str, Any]:
    """Load JSON schema from disk."""
    text = schema_path.read_text(encoding="utf-8")
    return yaml.safe_load(text)


def _iter_validation_messages(validator: Draft202012Validator, data: Mapping[str, Any]) -> Iterable[ValidationMessage]:
    """Yield formatted validation messages for *data*."""
    for error in validator.iter_errors(data):
        location = ".".join(str(part) for part in error.absolute_path)
        yield ValidationMessage(path=location or "<root>", message=error.message)


def validate_tournament_config(data: Mapping[str, Any], schema_path: Path | None = None) -> list[ValidationMessage]:
    """Validate *data* against the tournament schema and return issues."""
    effective_schema = _load_schema(schema_path or SCHEMA_FILE)
    validator = Draft202012Validator(effective_schema)
    return list(_iter_validation_messages(validator, data))


def load_tournament_config(path: Path, schema_path: Path | None = None) -> TournamentConfig:
    """Load and validate a tournament config file."""
    absolute_path = path if path.is_absolute() else Path.cwd() / path
    if not absolute_path.exists():
        raise FileNotFoundError(f"Config file '{path}' does not exist.")
    raw = _read_yaml(absolute_path)
    if not isinstance(raw, Mapping):
        raise TypeError("Tournament config must be a mapping at the top level.")
    messages = validate_tournament_config(raw, schema_path=schema_path)
    if messages:
        joined = "\n".join(f"[{m.path}] {m.message}" for m in messages)
        raise ValueError(f"Config validation failed:\n{joined}")
    return cast(TournamentConfig, raw)
