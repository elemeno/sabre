"""CLI command tests for saber."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from saber.cli import app

try:  # optional dependency for local adapters
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore


def _ollama_available() -> bool:
    if requests is None:
        return False
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        response = requests.get(f"{base_url.rstrip('/')}/api/version", timeout=1)
    except requests.RequestException:
        return False
    return response.ok


def _copy_config_tree(tmp_path: Path) -> Path:
    destination = tmp_path / "config"
    shutil.copytree(Path("config"), destination)
    return destination


def test_cli_validate_happy_path(tmp_path: Path) -> None:
    config_dir = _copy_config_tree(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["validate", "--config-dir", str(config_dir)], catch_exceptions=False)
    assert result.exit_code == 0
    assert "Configs OK" in result.stdout


def test_cli_run_match_emits_result_file(tmp_path: Path) -> None:
    if not _ollama_available():
        pytest.skip("Ollama not reachable")
    config_dir = _copy_config_tree(tmp_path)
    output_dir = tmp_path / "results"
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run-match",
            "--attacker",
            "llama2-7b",
            "--defender",
            "mistral-7b",
            "--exploit",
            "secret_extraction",
            "--persona",
            "direct_questioner",
            "--secret-index",
            "0",
            "--max-turns",
            "6",
            "--output-dir",
            str(output_dir),
            "--config-dir",
            str(config_dir),
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    files = list(output_dir.glob("match_*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text(encoding="utf-8"))
    assert data["meta"]["attacker"] == "llama2-7b"
    assert isinstance(data["transcript"], list) and data["transcript"]
    assert data["result"]["success"] is True
    assert data["runtime"]["turns"] == len(data["transcript"])
    assert data["result"]["confidence"] > 0.0


def test_cli_run_tournament_generates_summary(tmp_path: Path) -> None:
    if not _ollama_available():
        pytest.skip("Ollama not reachable")
    config_dir = _copy_config_tree(tmp_path)
    output_dir = tmp_path / "tournament"
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run",
            "--tournament",
            "MVP Basic",
            "--config-dir",
            str(config_dir),
            "--output-dir",
            str(output_dir),
            "--seed",
            "7",
            "--max-workers",
            "1",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    summary_path = output_dir / "tournament-summary.json"
    assert summary_path.exists()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    matches_dir = output_dir / "matches"
    assert matches_dir.exists()
    match_files = list(matches_dir.glob("*.json"))
    assert match_files
    assert summary["total_matches"] == len(match_files)
    assert summary["per_combo"]
    assert "pair_matrix" in summary


def test_cli_run_tournament_dry_run(tmp_path: Path) -> None:
    config_dir = _copy_config_tree(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run",
            "--tournament",
            "MVP Basic",
            "--config-dir",
            str(config_dir),
            "--dry-run",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "Planned matches" in result.stdout
    assert result.stdout.count("match_") >= 3
