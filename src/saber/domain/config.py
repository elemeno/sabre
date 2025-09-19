"""Domain models representing configuration artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


class ConfigError(Exception):
    """Raised when configuration files fail validation."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


@dataclass(frozen=True, kw_only=True)
class ModelCfg:
    path: Path = field(repr=False, compare=False)
    name: str
    adapter: str
    model_id: str
    runtime: Mapping[str, Any] | None = None
    notes: str | None = None


@dataclass(frozen=True, kw_only=True)
class PersonaCfg:
    path: Path = field(repr=False, compare=False)
    name: str
    description: str
    system_prompt: str
    opening_message: str
    meta: Mapping[str, Any] | None = None
    notes: str | None = None


@dataclass(frozen=True, kw_only=True)
class DetectionCfg:
    method: str
    params: Mapping[str, Any]


@dataclass(frozen=True, kw_only=True)
class ExploitCfg:
    path: Path = field(repr=False, compare=False)
    name: str
    description: str
    personas: list[str]
    defender_setup: str
    secrets: list[str]
    detection: DetectionCfg
    notes: str | None = None


@dataclass(frozen=True, kw_only=True)
class TournamentSettings:
    max_turns: int
    repetitions: int
    output_dir: str
    privacy_tier: str


@dataclass(frozen=True, kw_only=True)
class TournamentCfg:
    path: Path = field(repr=False, compare=False)
    name: str
    description: str
    models: list[str]
    exploits: list[str]
    settings: TournamentSettings
    notes: str | None = None


__all__ = [
    "ConfigError",
    "ModelCfg",
    "PersonaCfg",
    "DetectionCfg",
    "ExploitCfg",
    "TournamentSettings",
    "TournamentCfg",
]
