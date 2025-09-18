"""Command line entrypoints for Saber."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping

import typer
from rapidfuzz import process
from rich.console import Console
from rich.table import Table

from saber.config_loader import (
    ConfigError,
    TournamentCfg,
    collect_configs,
    load_tournament,
    validate_configs,
)
from saber.detectors import detect_config_issues
from saber.tournament import TournamentController

app = typer.Typer(help="Utility CLI for Saber configuration workflows.")
console = Console()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_DIR = PROJECT_ROOT / "config"


def _handle_config_error(exc: ConfigError) -> None:
    console.print(str(exc))
    raise typer.Exit(code=1) from exc


def _relative_name(path: Path) -> str:
    """Produce a display name relative to the config directory."""
    try:
        return str(path.relative_to(DEFAULT_CONFIG_DIR))
    except ValueError:
        return str(path)


def _suggest_tournament(target: str, tournaments: Mapping[str, TournamentCfg]) -> str | None:
    candidates = list(tournaments.keys())
    candidates.extend(_relative_name(cfg.path) for cfg in tournaments.values())
    if not candidates:
        return None
    match = process.extractOne(target, candidates, score_cutoff=65)
    return match[0] if match else None


def _resolve_tournament(identifier: str, tournaments: Mapping[str, TournamentCfg]) -> TournamentCfg:
    direct = tournaments.get(identifier)
    if direct is not None:
        return direct

    candidate = Path(identifier)
    candidate_paths = [candidate]
    if not candidate.is_absolute():
        candidate_paths.append(DEFAULT_CONFIG_DIR / "tournaments" / candidate)
        candidate_paths.append(DEFAULT_CONFIG_DIR / candidate)

    resolved = {path.resolve() for path in candidate_paths if path.suffix or path.exists()}
    for cfg in tournaments.values():
        cfg_path = cfg.path.resolve()
        if cfg_path in resolved or cfg_path.name == candidate.name or cfg_path.stem == candidate.stem:
            return cfg

    suggestion = _suggest_tournament(identifier, tournaments)
    hint = f" Did you mean '{suggestion}'?" if suggestion else ""
    raise ConfigError(
        f"[bold red]Config error[/bold red]: [cyan]{identifier}[/cyan] not found.{hint}"
    )


@app.command()
def list_configs() -> None:
    """Show available sample configurations."""
    try:
        _, _, _, tournaments = collect_configs(DEFAULT_CONFIG_DIR)
    except ConfigError as exc:
        _handle_config_error(exc)
        return

    if not tournaments:
        console.print("[yellow]No tournament files found in 'config/tournaments'.[/yellow]")
        return

    table = Table(title="Sample Tournaments")
    table.add_column("Name", justify="left")
    table.add_column("Path", justify="left")
    for cfg in sorted(tournaments.values(), key=lambda item: item.name):
        table.add_row(cfg.name, str(cfg.path))
    console.print(table)


@app.command()
def validate(identifier: str = typer.Argument(..., help="Tournament name or path")) -> None:
    """Validate a tournament configuration file."""
    try:
        models, personas, exploits, tournaments = collect_configs(DEFAULT_CONFIG_DIR)
        validate_configs(models, personas, exploits, tournaments)
        config = _resolve_tournament(identifier, tournaments)
    except ConfigError as exc:
        _handle_config_error(exc)
        return

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
def dry_run(identifier: str = typer.Argument(..., help="Tournament name or path")) -> None:
    """Run a dry tournament simulation using the dummy adapter."""
    try:
        config = load_tournament(identifier, DEFAULT_CONFIG_DIR)
    except ConfigError as exc:
        _handle_config_error(exc)
        return

    controller = TournamentController(config=config)
    console.print(controller.summary())
    for response in controller.dry_run():
        console.print(f"  • {response}")


def main(argv: Iterable[str] | None = None) -> None:
    """Invoke the Typer application."""
    app(args=list(argv) if argv is not None else None)


if __name__ == "__main__":
    main()
