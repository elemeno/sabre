"""Tests for configuration loading and validation."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from sabre.config_loader import (
    ConfigError,
    collect_configs,
    load_tournament,
    validate_configs,
)


def _copy_config_tree(tmp_path: Path) -> Path:
    destination = tmp_path / "config"
    shutil.copytree(Path("config"), destination)
    return destination


def test_full_config_suite_valid(tmp_path: Path) -> None:
    """The shipped sample configuration validates end-to-end."""
    config_dir = _copy_config_tree(tmp_path)
    models, personas, exploits, tournaments = collect_configs(config_dir)
    validate_configs(models, personas, exploits, tournaments)
    tournament = load_tournament("Full 3x3 Tournament", config_dir)
    assert tournament.name == "Full 3x3 Tournament"


def test_exploit_defender_setup_requires_placeholder(tmp_path: Path) -> None:
    """Missing {secret} placeholder should fail validation."""
    config_dir = _copy_config_tree(tmp_path)
    exploit_file = config_dir / "exploits" / "secret_extraction.yaml"
    text = exploit_file.read_text(encoding="utf-8")
    exploit_file.write_text(text.replace("{secret}", "SECRET"), encoding="utf-8")

    models, personas, exploits, tournaments = collect_configs(config_dir)
    with pytest.raises(ConfigError) as excinfo:
        validate_configs(models, personas, exploits, tournaments)
    assert "defender_setup" in str(excinfo.value)
    assert "{secret}" in str(excinfo.value)


def test_exploit_persona_reference_must_exist(tmp_path: Path) -> None:
    """Exploit referencing unknown persona raises ConfigError."""
    config_dir = _copy_config_tree(tmp_path)
    exploit_file = config_dir / "exploits" / "secret_extraction.yaml"
    text = exploit_file.read_text(encoding="utf-8")
    exploit_file.write_text(
        text.replace("- \"social_engineer\"", "- \"ghost_persona\""),
        encoding="utf-8",
    )

    models, personas, exploits, tournaments = collect_configs(config_dir)
    with pytest.raises(ConfigError) as excinfo:
        validate_configs(models, personas, exploits, tournaments)
    assert "ghost_persona" in str(excinfo.value)


def test_tournament_model_reference_must_exist(tmp_path: Path) -> None:
    """Tournament referencing unknown model raises ConfigError."""
    config_dir = _copy_config_tree(tmp_path)
    tournament_file = config_dir / "tournaments" / "full_3x3.yaml"
    import yaml

    data = yaml.safe_load(tournament_file.read_text(encoding="utf-8"))
    data["models"][0] = "ghost-model"
    tournament_file.write_text(yaml.safe_dump(data), encoding="utf-8")

    models, personas, exploits, tournaments = collect_configs(config_dir)
    with pytest.raises(ConfigError) as excinfo:
        validate_configs(models, personas, exploits, tournaments)
    assert "ghost-model" in str(excinfo.value)
