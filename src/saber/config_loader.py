"""Compatibility layer for configuration utilities."""

from __future__ import annotations

from saber.domain.config import (
    ConfigError,
    DetectionCfg,
    ExploitCfg,
    ModelCfg,
    PersonaCfg,
    TournamentCfg,
    TournamentSettings,
)
from saber.infrastructure.config.loader import collect_configs, load_tournament
from saber.infrastructure.config.validators import validate_configs

__all__ = [
    "ConfigError",
    "ModelCfg",
    "PersonaCfg",
    "DetectionCfg",
    "ExploitCfg",
    "TournamentSettings",
    "TournamentCfg",
    "collect_configs",
    "validate_configs",
    "load_tournament",
]
