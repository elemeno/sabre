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
from saber.detectors import run_detection
from saber.tournament import MatchSpec, TournamentController

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


@app.command("run")
def run_tournament(
    tournament: str = typer.Option(..., "--tournament", help="Tournament name or path."),
    config_dir: Path = typer.Option(
        default=_config_dir_option(),
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        help="Directory containing Saber configuration YAML files.",
    ),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        file_okay=False,
        dir_okay=True,
        readable=False,
        writable=True,
        help="Destination for tournament artefacts (defaults to the tournament setting).",
    ),
    seed: int = typer.Option(42, "--seed", help="Seed used for persona and secret rotation."),
    max_workers: int = typer.Option(1, "--max-workers", min=1, help="Number of workers (future use)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the planned schedule without running matches."),
) -> None:
    """Run an entire tournament schedule."""

    models, personas, exploits, tournaments = _load_and_validate(config_dir)
    tournament_cfg = tournaments.get(tournament)
    if tournament_cfg is None:
        try:
            tournament_cfg = load_tournament(tournament, config_dir)
        except ConfigError as exc:
            _handle_config_error(exc)
            return

    effective_output_dir = output_dir or Path(tournament_cfg.settings.output_dir)
    if not effective_output_dir.is_absolute():
        effective_output_dir = (config_dir / effective_output_dir).resolve()
    effective_output_dir.mkdir(parents=True, exist_ok=True)

    def _match_runner(spec: MatchSpec, destination: Path) -> dict[str, Any]:
        return _simulate_match(
            attacker_cfg=spec.attacker,
            defender_cfg=spec.defender,
            exploit_cfg=spec.exploit,
            persona_cfg=spec.persona,
            defender_prompt=spec.defender_prompt,
            secret=spec.secret,
            secret_index=spec.secret_index,
            max_turns=spec.turn_limit,
            output_dir=destination,
            match_id=spec.match_id,
        )

    controller = TournamentController(
        config=tournament_cfg,
        models=models,
        personas=personas,
        exploits=exploits,
        run_match_fn=_match_runner,
        seed=seed,
    )

    schedule = controller.build_schedule()

    if dry_run:
        console.print(f"Planned matches: {len(schedule)}")
        preview = schedule[:3]
        for spec in preview:
            console.print(
                f"  {spec.match_id}: {spec.attacker.name} -> {spec.defender.name} | {spec.exploit.name} | persona={spec.persona.name} | secret_index={spec.secret_index}"
            )
        if len(schedule) > 3:
            console.print(f"  ... ({len(schedule) - 3} more matches)")
        return

    try:
        result = controller.run(output_dir=effective_output_dir, max_workers=max_workers)
    except NotImplementedError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    _print_tournament_matrix(tournament_cfg, result.aggregates.get("pair_matrix", {}))

    attacker_rows = result.aggregates.get("attacker_effectiveness", [])
    if attacker_rows:
        console.print("\n[bold]Attacker effectiveness[/bold]")
        for entry in attacker_rows:
            console.print(
                f"  {entry['model']}: {entry['score'] * 100:.1f}% success across {int(entry['total'])} matches"
            )

    defender_rows = result.aggregates.get("defender_robustness", [])
    if defender_rows:
        console.print("\n[bold]Defender robustness[/bold]")
        for entry in defender_rows:
            console.print(
                f"  {entry['model']}: {entry['score'] * 100:.1f}% prevention across {int(entry['total'])} matches"
            )

    total_matches = result.aggregates.get("total_matches", len(result.matches))
    console.print(
        f"\n[green]Tournament complete:[/green] {total_matches} matches"
    )
    console.print(f"Summary JSON: {result.summary_path}")
    console.print(f"Summary CSV: {result.csv_path}")
    console.print(f"Match artefacts: {result.matches_dir}")


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
    match_id: str | None = None,
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
    turns_to_success: int | None = None
    detection_confidence = 0.0
    detection_details: dict[str, object] | None = None

    while turns < max_turns:
        defender_message = DummyAdapter.defender_response(
            defender_prompt=defender_prompt,
            attacker_message=attacker_message,
            secret=secret,
        )
        transcript.append({"role": "defender", "content": defender_message})
        turns += 1

        try:
            detected, confidence, details = run_detection(
                exploit_cfg.detection.method,
                dict(exploit_cfg.detection.params),
                defender_message,
                secret,
            )
        except NotImplementedError as exc:
            console.print(f"[red]Detection failed:[/red] {exc}")
            raise typer.Exit(code=1) from exc
        transcript[-1]["detection"] = {
            "method": exploit_cfg.detection.method,
            "confidence": confidence,
            "details": details,
        }
        detection_confidence = confidence
        detection_details = details

        if detected:
            success = True
            reason = "secret_revealed"
            turns_to_success = len(transcript)
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
        match_id=match_id,
    )
    output_path = output_dir / filename
    resolved_match_id = match_id or Path(filename).stem

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
            "match_id": resolved_match_id,
            "output_path": str(output_path),
        },
        "result": {
            "success": success,
            "reason": reason,
            "confidence": detection_confidence,
            "details": detection_details or {},
        },
        "transcript": transcript,
        "runtime": {
            "turns": len(transcript),
            "elapsed_seconds": round(elapsed, 4),
            "turns_to_success": turns_to_success,
        },
    }

    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    return payload


def _print_tournament_matrix(tournament: TournamentCfg, matrix: dict[str, dict[str, float]]) -> None:
    table = Table(title=f"Success Rate – {tournament.name}")
    defenders = list(tournament.models)
    table.add_column("Attacker \\ Defender", justify="left")
    for defender in defenders:
        table.add_column(defender, justify="right")

    for attacker in tournament.models:
        row = [attacker]
        attacker_row = matrix.get(attacker, {})
        for defender in defenders:
            rate = attacker_row.get(defender)
            display = f"{rate * 100:.1f}%" if rate is not None else "—"
            row.append(display)
        table.add_row(*row)

    console.print(table)


def _match_filename(
    *,
    attacker: str,
    defender: str,
    exploit: str,
    secret_index: int,
    match_id: str | None = None,
) -> str:
    if match_id:
        return match_id if match_id.endswith(".json") else f"{match_id}.json"
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
