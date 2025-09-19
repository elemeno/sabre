"""Contract tests for configuration loading and validation."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from saber.config_loader import (
    ConfigError,
    ModelCfg,
    PersonaCfg,
    ExploitCfg,
    TournamentCfg,
    collect_configs,
    validate_configs,
)


def _copy_config(tmp_path: Path) -> Path:
    dest = tmp_path / "config"
    shutil.copytree(Path("config"), dest)
    return dest


def test_collect_configs_returns_domain_objects(tmp_path: Path) -> None:
    config_dir = _copy_config(tmp_path)
    models, personas, exploits, tournaments = collect_configs(config_dir)

    assert isinstance(models["llama2-7b"], ModelCfg)
    assert isinstance(personas["direct_questioner"], PersonaCfg)
    assert isinstance(exploits["secret_extraction"], ExploitCfg)
    assert isinstance(tournaments["Full 3x3 Tournament"], TournamentCfg)


def test_validate_configs_rejects_missing_persona(tmp_path: Path) -> None:
    config_dir = _copy_config(tmp_path)
    models, personas, exploits, tournaments = collect_configs(config_dir)
    personas.pop("direct_questioner")
    with pytest.raises(ConfigError) as excinfo:
        validate_configs(models, personas, exploits, tournaments)
    assert "Referenced persona is not defined" in str(excinfo.value)
