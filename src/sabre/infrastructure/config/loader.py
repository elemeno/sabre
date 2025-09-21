"""Config loading utilities coordinating schema validation and parsing."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Tuple

import yaml

from sabre.domain.config import (
    ConfigError,
    DetectionCfg,
    ExploitCfg,
    ModelCfg,
    PersonaCfg,
    TournamentCfg,
    TournamentSettings,
)
from .validators import (
    _ALLOWED_DETECTION_METHODS,
    build_validator,
    format_error,
    validate_configs,
    validate_with_schema,
)

__all__ = ["collect_configs", "load_tournament", "validate_configs"]


def _read_yaml(path: Path) -> Mapping[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover - filesystem error propagation
        raise ConfigError(format_error(path, "<file>", str(exc))) from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(format_error(path, "<root>", f"Invalid YAML: {exc}")) from exc
    if not isinstance(data, Mapping):
        raise ConfigError(format_error(path, "<root>", "Top-level document must be a mapping."))
    return data


def _ensure_unique(name: str, seen: Dict[str, Path], path: Path, kind: str) -> None:
    existing = seen.get(name)
    if existing is not None:
        raise ConfigError(
            format_error(
                path,
                "name",
                f"Duplicate {kind} identifier '{name}' already defined in {existing}",
            )
        )
    seen[name] = path


def _build_model(data: Mapping[str, Any], path: Path) -> ModelCfg:
    runtime = data.get("runtime")
    if runtime is not None and not isinstance(runtime, Mapping):
        raise ConfigError(format_error(path, "runtime", "Runtime must be a mapping when provided."))
    return ModelCfg(
        path=path,
        name=str(data["name"]),
        adapter=str(data["adapter"]),
        model_id=str(data["model_id"]),
        runtime=dict(runtime) if isinstance(runtime, Mapping) else None,
        notes=data.get("notes"),
        preprocess=data.get("preprocess"),
        postprocess=data.get("postprocess"),
    )


def _build_persona(data: Mapping[str, Any], path: Path) -> PersonaCfg:
    meta = data.get("meta")
    if meta is not None and not isinstance(meta, Mapping):
        raise ConfigError(format_error(path, "meta", "Meta must be a mapping when provided."))
    return PersonaCfg(
        path=path,
        name=str(data["name"]),
        description=str(data["description"]),
        system_prompt=str(data["system_prompt"]),
        opening_message=str(data["opening_message"]),
        meta=dict(meta) if isinstance(meta, Mapping) else None,
        notes=data.get("notes"),
    )


def _build_detection(data: Mapping[str, Any], path: Path) -> DetectionCfg:
    method = str(data["method"])
    if method not in _ALLOWED_DETECTION_METHODS:
        raise ConfigError(
            format_error(
                path,
                "detection.method",
                f"Unsupported detection method '{method}'.",
            )
        )
    params = data.get("params") or {}
    if not isinstance(params, Mapping):
        raise ConfigError(
            format_error(path, "detection.params", "Params must be a mapping when provided."))
    return DetectionCfg(method=method, params=dict(params))


def _build_exploit(data: Mapping[str, Any], path: Path) -> ExploitCfg:
    detection = _build_detection(data["detection"], path)
    return ExploitCfg(
        path=path,
        name=str(data["name"]),
        description=str(data["description"]),
        personas=list(data["personas"]),
        defender_setup=str(data["defender_setup"]),
        secrets=list(data["secrets"]),
        detection=detection,
        notes=data.get("notes"),
    )


def _build_settings(data: Mapping[str, Any]) -> TournamentSettings:
    return TournamentSettings(
        max_turns=int(data["max_turns"]),
        repetitions=int(data["repetitions"]),
        output_dir=str(data["output_dir"]),
        privacy_tier=str(data["privacy_tier"]),
    )


def _build_tournament(data: Mapping[str, Any], path: Path) -> TournamentCfg:
    settings = _build_settings(data["settings"])
    return TournamentCfg(
        path=path,
        name=str(data["name"]),
        description=str(data["description"]),
        models=list(data["models"]),
        exploits=list(data["exploits"]),
        settings=settings,
        notes=data.get("notes"),
    )


def _gather(directory: Path) -> Iterable[Path]:
    if not directory.exists():
        raise ConfigError(format_error(directory, "<dir>", "Required configuration directory is missing."))
    return sorted(directory.glob("*.yaml"))


def collect_configs(
    base_dir: Path,
) -> Tuple[dict[str, ModelCfg], dict[str, PersonaCfg], dict[str, ExploitCfg], dict[str, TournamentCfg]]:
    base_dir = base_dir.resolve()
    validator = build_validator()

    model_dir = base_dir / "models"
    persona_dir = base_dir / "personas"
    exploit_dir = base_dir / "exploits"
    tournament_dir = base_dir / "tournaments"

    models: dict[str, ModelCfg] = {}
    personas: dict[str, PersonaCfg] = {}
    exploits: dict[str, ExploitCfg] = {}
    tournaments: dict[str, TournamentCfg] = {}

    seen_models: dict[str, Path] = {}
    seen_personas: dict[str, Path] = {}
    seen_exploits: dict[str, Path] = {}
    seen_tournaments: dict[str, Path] = {}

    for path in _gather(model_dir):
        data = _read_yaml(path)
        validate_with_schema(validator, data, "#/$defs/model", path)
        cfg = _build_model(data, path)
        _ensure_unique(cfg.name, seen_models, path, "model")
        models[cfg.name] = cfg

    for path in _gather(persona_dir):
        data = _read_yaml(path)
        validate_with_schema(validator, data, "#/$defs/persona", path)
        cfg = _build_persona(data, path)
        _ensure_unique(cfg.name, seen_personas, path, "persona")
        personas[cfg.name] = cfg

    for path in _gather(exploit_dir):
        data = _read_yaml(path)
        validate_with_schema(validator, data, "#/$defs/exploit", path)
        cfg = _build_exploit(data, path)
        _ensure_unique(cfg.name, seen_exploits, path, "exploit")
        exploits[cfg.name] = cfg

    for path in _gather(tournament_dir):
        data = _read_yaml(path)
        validate_with_schema(validator, data, "#/$defs/tournament", path)
        cfg = _build_tournament(data, path)
        _ensure_unique(cfg.name, seen_tournaments, path, "tournament")
        tournaments[cfg.name] = cfg

    return models, personas, exploits, tournaments


def load_tournament(identifier: str | Path, base_dir: Path | None = None) -> TournamentCfg:
    """Load a tournament configuration by path or name."""

    base_dir = base_dir or Path.cwd()
    models, personas, exploits, tournaments = collect_configs(base_dir)
    validate_configs(models, personas, exploits, tournaments)

    if isinstance(identifier, str) and identifier in tournaments:
        return tournaments[identifier]

    candidate = Path(identifier) if not isinstance(identifier, Path) else identifier
    candidate = candidate if candidate.is_absolute() else base_dir / "tournaments" / candidate
    candidate = candidate.resolve()

    for cfg in tournaments.values():
        if cfg.path.resolve() == candidate:
            return cfg

    raise ConfigError(format_error(candidate, "name", "Tournament not found."))
