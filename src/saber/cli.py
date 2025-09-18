"""Command line interface for Saber."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Iterable

import typer
from rich.console import Console
from rich.table import Table

from saber.config_loader import (
    ConfigError,
    ExploitCfg,
    ModelCfg,
    PersonaCfg,
    TournamentCfg,
    collect_configs,
    load_tournament,
    validate_configs,
)
from saber.adapters import DummyAdapter

app = typer.Typer(help="CLI for Saber configuration management and match simulation.")
console = Console()


def _config_dir_option(default: str = "config") -> Path:
    return Path(default)


def _handle_config_error(exc: ConfigError) -> None:
    console.print(str(exc))
    raise typer.Exit(code=1) from exc


def _load_and_validate(config_dir: Path) -> tuple[
    dict[str, ModelCfg],
    dict[str, PersonaCfg],
    dict[str, ExploitCfg],
    dict[str, TournamentCfg],
]:
    try:
        models, personas, exploits, tournaments = collect_configs(config_dir)
        validate_configs(models, personas, exploits, tournaments)
        return models, personas, exploits, tournaments
    except ConfigError as exc:
        _handle_config_error(exc)
        raise  # pragma: no cover


@app.command()
def validate(
    config_dir: Path = typer.Option(
        default=_config_dir_option(),
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        help="Directory containing Saber configuration YAML files.",
    )
) -> None:
    """Validate configuration files."""

    _load_and_validate(config_dir)
    console.print("[green]Configs OK[/green]")


@app.command()
def show(
    subject: str = typer.Argument(..., help="Entity to show. Currently only 'tournament'."),
    name: str = typer.Argument(..., help="Name of the tournament."),
    config_dir: Path = typer.Option(
        default=_config_dir_option(),
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        help="Directory containing Saber configuration YAML files.",
    ),
) -> None:
    """Display details about a configuration entity."""

    if subject != "tournament":
        console.print("[red]Only 'tournament' is supported for show.[/red]")
        raise typer.Exit(code=1)

    try:
        tournament = load_tournament(name, config_dir)
    except ConfigError as exc:
        _handle_config_error(exc)
        return

    _print_tournament_details(tournament)


def _print_tournament_details(tournament: TournamentCfg) -> None:
    console.print(f"[bold]Tournament:[/bold] {tournament.name}")
    console.print(f"Description: {tournament.description}")
    console.print("")

    table = Table(title="Tournament Overview")
    table.add_column("Field", justify="left")
    table.add_column("Value", justify="left")
    table.add_row("Models", ", ".join(tournament.models))
    table.add_row("Exploits", ", ".join(tournament.exploits))
    settings = tournament.settings
    table.add_row("Max Turns", str(settings.max_turns))
    table.add_row("Repetitions", str(settings.repetitions))
    table.add_row("Output Dir", settings.output_dir)
    table.add_row("Privacy Tier", settings.privacy_tier)
    console.print(table)


@app.command()
def run_match(
    attacker: str = typer.Option(..., "--attacker", help="Attacker model name."),
    defender: str = typer.Option(..., "--defender", help="Defender model name."),
    exploit: str = typer.Option(..., "--exploit", help="Exploit scenario name."),
    persona: str = typer.Option(..., "--persona", help="Persona name for attacker."),
    secret_index: int = typer.Option(..., "--secret-index", help="Secret index to target."),
    max_turns: int = typer.Option(6, "--max-turns", min=2, help="Maximum number of turns."),
    output_dir: Path = typer.Option(
        Path("results"),
        "--output-dir",
        file_okay=False,
        dir_okay=True,
        help="Directory to store match results.",
    ),
    config_dir: Path = typer.Option(
        default=_config_dir_option(),
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        help="Directory containing Saber configuration YAML files.",
    ),
) -> None:
    """Run a deterministic dummy match."""

    models, personas_map, exploits, _ = _load_and_validate(config_dir)

    attacker_cfg = _require_entity(attacker, models, "model", config_dir)
    defender_cfg = _require_entity(defender, models, "model", config_dir)
    exploit_cfg = _require_entity(exploit, exploits, "exploit", config_dir)
    persona_cfg = _require_entity(persona, personas_map, "persona", config_dir)

    if persona_cfg.name not in exploit_cfg.personas:
        console.print(
            f"[red]Persona '{persona_cfg.name}' is not allowed for exploit '{exploit_cfg.name}'.[/red]"
        )
        raise typer.Exit(code=1)

    if secret_index < 0 or secret_index >= len(exploit_cfg.secrets):
        console.print(
            f"[red]Secret index {secret_index} is out of range for exploit '{exploit_cfg.name}'.[/red]"
        )
        raise typer.Exit(code=1)

    secret = exploit_cfg.secrets[secret_index]
    defender_prompt = exploit_cfg.defender_setup.replace("{secret}", secret)

    result = _simulate_match(
        attacker_cfg=attacker_cfg,
        defender_cfg=defender_cfg,
        exploit_cfg=exploit_cfg,
        persona_cfg=persona_cfg,
        defender_prompt=defender_prompt,
        secret=secret,
        secret_index=secret_index,
        max_turns=max_turns,
        output_dir=output_dir,
    )

    status = "SUCCESS" if result["result"]["success"] else "FAILURE"
    color = "green" if result["result"]["success"] else "red"
    console.print(
        f"[{color}]Match {status}[/] – {result['result']['reason']} (turns={result['runtime']['turns']})."
        f" Result saved to {result['meta']['output_path']}"
    )


def _require_entity(name: str, store: dict[str, Any], kind: str, config_dir: Path) -> Any:
    entity = store.get(name)
    if entity is None:
        console.print(
            f"[red]Unknown {kind} '{name}'. Available: {', '.join(sorted(store.keys()))}[/red]"
        )
        raise typer.Exit(code=1)
    return entity


def _simulate_match(
    *,
    attacker_cfg: ModelCfg,
    defender_cfg: ModelCfg,
    exploit_cfg: ExploitCfg,
    persona_cfg: PersonaCfg,
    defender_prompt: str,
    secret: str,
    secret_index: int,
    max_turns: int,
    output_dir: Path,
) -> dict[str, Any]:
    start_time = time.monotonic()
    transcript: list[dict[str, str]] = []

    _attacker_adapter = DummyAdapter(name=f"attacker::{attacker_cfg.name}")
    _defender_adapter = DummyAdapter(name=f"defender::{defender_cfg.name}")

    attacker_message = persona_cfg.opening_message
    transcript.append({"role": "attacker", "content": attacker_message})
    turns = 1
    success = False
    reason = "turn_limit_reached"

    while turns < max_turns:
        defender_message = DummyAdapter.defender_response(
            defender_prompt=defender_prompt,
            attacker_message=attacker_message,
            secret=secret,
        )
        transcript.append({"role": "defender", "content": defender_message})
        turns += 1

        if secret in defender_message:
            success = True
            reason = "secret_revealed"
            break

        if turns >= max_turns:
            reason = "turn_limit_reached"
            break

        attacker_message = DummyAdapter.attacker_response(
            persona_question=persona_cfg.opening_message,
            last_defender_message=defender_message,
        )
        transcript.append({"role": "attacker", "content": attacker_message})
        turns += 1

    elapsed = time.monotonic() - start_time
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = _match_filename(
        attacker=attacker_cfg.name,
        defender=defender_cfg.name,
        exploit=exploit_cfg.name,
        secret_index=secret_index,
    )
    output_path = output_dir / filename

    payload = {
        "meta": {
            "attacker": attacker_cfg.name,
            "defender": defender_cfg.name,
            "exploit": exploit_cfg.name,
            "persona": persona_cfg.name,
            "secret_index": secret_index,
            "max_turns": max_turns,
            "defender_prompt": defender_prompt,
            "attacker_adapter": _attacker_adapter.name,
            "defender_adapter": _defender_adapter.name,
            "output_path": str(output_path),
        },
        "result": {
            "success": success,
            "reason": reason,
        },
        "transcript": transcript,
        "runtime": {
            "turns": len(transcript),
            "elapsed_seconds": round(elapsed, 4),
        },
    }

    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    return payload


def _match_filename(*, attacker: str, defender: str, exploit: str, secret_index: int) -> str:
    safe = "_".join(
        part.replace(" ", "-")
        for part in (attacker, defender, exploit, f"secret{secret_index}")
    )
    timestamp = int(time.time())
    return f"match_{safe}_{timestamp}.json"


def main(argv: Iterable[str] | None = None) -> None:
    """Invoke the Typer application."""
    app(args=list(argv) if argv is not None else None)


if __name__ == "__main__":
    main()
