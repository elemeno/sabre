"""Command line entrypoints for Saber."""

from __future__ import annotations

from pathlib import Path

import typer
from rapidfuzz import process
from rich.console import Console
from rich.table import Table

from saber.config_loader import TournamentConfig, load_tournament_config
from saber.detectors import detect_config_issues
from saber.tournament import TournamentController

app = typer.Typer(help="Utility CLI for Saber configuration workflows.")
console = Console()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_DIR = PROJECT_ROOT / "config"


def _available_config_paths() -> list[Path]:
    """Return all YAML config files in the default directory."""
    if not DEFAULT_CONFIG_DIR.exists():
        return []
    return sorted(DEFAULT_CONFIG_DIR.rglob("*.yaml"))


def _relative_name(path: Path) -> str:
    """Produce a display name relative to the config directory."""
    try:
        return str(path.relative_to(DEFAULT_CONFIG_DIR))
    except ValueError:
        return str(path)


def _suggest_config(target: str) -> str | None:
    """Suggest the closest matching config filename using fuzzy matching."""
    candidates = [_relative_name(path) for path in _available_config_paths()]
    if not candidates:
        return None
    match = process.extractOne(target, candidates, score_cutoff=65)
    return match[0] if match else None


def _maybe_from_default_dir(config_path: Path) -> Path:
    """Resolve *config_path* relative to the default directory when possible."""
    if config_path.exists():
        return config_path
    fallback = DEFAULT_CONFIG_DIR / config_path
    return fallback if fallback.exists() else config_path


def _load_config_or_exit(config_path: Path) -> TournamentConfig:
    """Load a configuration file or exit with an error message."""
    resolved = _maybe_from_default_dir(config_path)
    try:
        return load_tournament_config(resolved)
    except FileNotFoundError as exc:
        suggestion = _suggest_config(config_path.as_posix())
        hint = f" Did you mean '{suggestion}'?" if suggestion else ""
        console.print(f"[red]Error:[/red] {exc}{hint}")
        raise typer.Exit(code=1) from exc
    except (TypeError, ValueError) as exc:
        console.print(f"[red]Validation failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc


@app.command()
def list_configs() -> None:
    """Show available sample configurations."""
    paths = _available_config_paths()
    if not paths:
        console.print("[yellow]No configuration files found in 'config/'.[/yellow]")
        return
    table = Table(title="Sample Configurations")
    table.add_column("Name", justify="left")
    table.add_column("Path", justify="left")
    for path in paths:
        table.add_row(_relative_name(path), str(path))
    console.print(table)


@app.command()
def validate(config_path: Path = typer.Argument(..., exists=False, dir_okay=False, readable=True)) -> None:
    """Validate a tournament configuration file."""
    config = _load_config_or_exit(config_path)
    issues = detect_config_issues(config)
    if issues:
        table = Table(title="Heuristic Findings")
        table.add_column("Severity")
        table.add_column("Message")
        for issue in issues:
            table.add_row(issue.severity, issue.message)
        console.print(table)
    console.print("[green]Config validation succeeded.[/green]")


@app.command()
def dry_run(config_path: Path = typer.Argument(..., exists=False, dir_okay=False, readable=True)) -> None:
    """Run a dry tournament simulation using the dummy adapter."""
    config = _load_config_or_exit(config_path)
    controller = TournamentController(config=config)
    console.print(controller.summary())
    for response in controller.dry_run():
        console.print(f"  • {response}")


def main() -> None:
    """Invoke the Typer application."""
    app()


if __name__ == "__main__":
    main()
