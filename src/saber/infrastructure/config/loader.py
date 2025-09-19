"""Config loading and validation utilities for Saber."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Tuple

import yaml
from jsonschema import Draft202012Validator, ValidationError

SCHEMA_FILE = Path(__file__).resolve().parent / "schemas" / "config-schema.json"


class ConfigError(Exception):
    """Raised when configuration files fail validation."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


@dataclass(frozen=True, kw_only=True)
class ModelCfg:
    """Configuration for a model adapter."""

    path: Path = field(repr=False, compare=False)
    name: str
    adapter: str
    model_id: str
    runtime: Mapping[str, Any] | None = None
    notes: str | None = None


@dataclass(frozen=True, kw_only=True)
class PersonaCfg:
    """Configuration describing an attacking persona."""

    path: Path = field(repr=False, compare=False)
    name: str
    description: str
    system_prompt: str
    opening_message: str
    meta: Mapping[str, Any] | None = None
    notes: str | None = None


@dataclass(frozen=True, kw_only=True)
class DetectionCfg:
    """Detection strategy for an exploit."""

    method: str
    params: Mapping[str, Any]


@dataclass(frozen=True, kw_only=True)
class ExploitCfg:
    """Configuration for an exploit scenario."""

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
    """Runtime settings for tournaments."""

    max_turns: int
    repetitions: int
    output_dir: str
    privacy_tier: str


@dataclass(frozen=True, kw_only=True)
class TournamentCfg:
    """Configuration for tournaments."""

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
    "collect_configs",
    "validate_configs",
    "load_tournament",
]

_ALLOWED_DETECTION_METHODS: tuple[str, ...] = (
    "exact_match",
    "regex",
    "fuzzy_match",
    "embedding",
)


def _format_error(path: Path, field: str, message: str) -> str:
    location = f"[cyan]{path}[/cyan]"
    target = f" → [magenta]{field}[/magenta]" if field else ""
    return f"[bold red]Config error[/bold red]: {location}{target} {message}"


def _load_schema() -> Mapping[str, Any]:
    schema_text = SCHEMA_FILE.read_text(encoding="utf-8")
    return yaml.safe_load(schema_text)


def _read_yaml(path: Path) -> Mapping[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover - filesystem error propagation
        raise ConfigError(_format_error(path, "<file>", str(exc))) from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(_format_error(path, "<root>", f"Invalid YAML: {exc}")) from exc
    if not isinstance(data, Mapping):
        raise ConfigError(_format_error(path, "<root>", "Top-level document must be a mapping."))
    return data


def _validator() -> Draft202012Validator:
    schema = _load_schema()
    return Draft202012Validator(schema)


def _validate_with_schema(
    validator: Draft202012Validator,
    instance: Mapping[str, Any],
    ref: str,
    path: Path,
) -> None:
    try:
        validator.evolve(schema={"$ref": ref}).validate(instance)
    except ValidationError as exc:
        field = "/".join(str(part) for part in exc.path)
        field_display = field or "<root>"
        raise ConfigError(_format_error(path, field_display, exc.message)) from exc


def _ensure_unique(name: str, seen: Dict[str, Path], path: Path, kind: str) -> None:
    existing = seen.get(name)
    if existing is not None:
        raise ConfigError(
            _format_error(
                path,
                "name",
                f"Duplicate {kind} identifier '{name}' already defined in {existing}",
            )
        )
    seen[name] = path


def _build_model(data: Mapping[str, Any], path: Path) -> ModelCfg:
    runtime = data.get("runtime")
    if runtime is not None and not isinstance(runtime, Mapping):
        raise ConfigError(_format_error(path, "runtime", "Runtime must be a mapping when provided."))
    return ModelCfg(
        path=path,
        name=str(data["name"]),
        adapter=str(data["adapter"]),
        model_id=str(data["model_id"]),
        runtime=dict(runtime) if isinstance(runtime, Mapping) else None,
        notes=data.get("notes"),
    )


def _build_persona(data: Mapping[str, Any], path: Path) -> PersonaCfg:
    meta = data.get("meta")
    if meta is not None and not isinstance(meta, Mapping):
        raise ConfigError(_format_error(path, "meta", "Meta must be a mapping when provided."))
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
            _format_error(
                path,
                "detection.method",
                f"Unsupported detection method '{method}'.",
            )
        )
    params = data.get("params") or {}
    if not isinstance(params, Mapping):
        raise ConfigError(
            _format_error(path, "detection.params", "Params must be a mapping when provided."))
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
        raise ConfigError(_format_error(directory, "<dir>", "Required configuration directory is missing."))
    return sorted(directory.glob("*.yaml"))


def collect_configs(
    base_dir: Path,
) -> Tuple[dict[str, ModelCfg], dict[str, PersonaCfg], dict[str, ExploitCfg], dict[str, TournamentCfg]]:
    """Collect all configuration files beneath *base_dir*."""

    base_dir = base_dir.resolve()
    validator = _validator()

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
        _validate_with_schema(validator, data, "#/$defs/model", path)
        cfg = _build_model(data, path)
        _ensure_unique(cfg.name, seen_models, path, "model")
        models[cfg.name] = cfg

    for path in _gather(persona_dir):
        data = _read_yaml(path)
        _validate_with_schema(validator, data, "#/$defs/persona", path)
        cfg = _build_persona(data, path)
        _ensure_unique(cfg.name, seen_personas, path, "persona")
        personas[cfg.name] = cfg

    for path in _gather(exploit_dir):
        data = _read_yaml(path)
        _validate_with_schema(validator, data, "#/$defs/exploit", path)
        cfg = _build_exploit(data, path)
        _ensure_unique(cfg.name, seen_exploits, path, "exploit")
        exploits[cfg.name] = cfg

    for path in _gather(tournament_dir):
        data = _read_yaml(path)
        _validate_with_schema(validator, data, "#/$defs/tournament", path)
        cfg = _build_tournament(data, path)
        _ensure_unique(cfg.name, seen_tournaments, path, "tournament")
        tournaments[cfg.name] = cfg

    return models, personas, exploits, tournaments


def _dataclass_payload(instance: Any) -> Mapping[str, Any]:
    data = asdict(instance)
    data.pop("path", None)
    return {key: value for key, value in data.items() if value is not None}


def validate_configs(
    models: Mapping[str, ModelCfg],
    personas: Mapping[str, PersonaCfg],
    exploits: Mapping[str, ExploitCfg],
    tournaments: Mapping[str, TournamentCfg],
) -> None:
    """Validate configs using JSON Schema and additional invariants."""

    validator = _validator()

    for cfg in models.values():
        _validate_with_schema(validator, _dataclass_payload(cfg), "#/$defs/model", cfg.path)

    for cfg in personas.values():
        _validate_with_schema(validator, _dataclass_payload(cfg), "#/$defs/persona", cfg.path)

    for cfg in exploits.values():
        payload = dict(_dataclass_payload(cfg))
        payload["detection"] = asdict(cfg.detection)
        _validate_with_schema(validator, payload, "#/$defs/exploit", cfg.path)
        if "{secret}" not in cfg.defender_setup:
            raise ConfigError(
                _format_error(
                    cfg.path,
                    "defender_setup",
                    "Defender setup must contain the '{secret}' placeholder.",
                )
            )
        for persona_name in cfg.personas:
            if persona_name not in personas:
                raise ConfigError(
                    _format_error(
                        cfg.path,
                        f"personas[{persona_name}]",
                        "Referenced persona is not defined.",
                    )
                )

    for cfg in tournaments.values():
        payload = dict(_dataclass_payload(cfg))
        payload["settings"] = asdict(cfg.settings)
        _validate_with_schema(validator, payload, "#/$defs/tournament", cfg.path)
        for model_name in cfg.models:
            if model_name not in models:
                raise ConfigError(
                    _format_error(
                        cfg.path,
                        f"models[{model_name}]",
                        "Referenced model is not defined.",
                    )
                )
        for exploit_name in cfg.exploits:
            if exploit_name not in exploits:
                raise ConfigError(
                    _format_error(
                        cfg.path,
                        f"exploits[{exploit_name}]",
                        "Referenced exploit is not defined.",
                    )
                )


def load_tournament(name: str, base_dir: Path) -> TournamentCfg:
    """Load and return a validated tournament configuration by *name*."""

    models, personas, exploits, tournaments = collect_configs(base_dir)
    validate_configs(models, personas, exploits, tournaments)

    target = tournaments.get(name)
    if target is not None:
        return target

    candidate_path = Path(name)
    candidate_paths = [candidate_path]
    if not candidate_path.is_absolute():
        candidate_paths.append(base_dir / "tournaments" / candidate_path)
        candidate_paths.append(base_dir / candidate_path)

    resolved_candidates = {path.resolve() for path in candidate_paths if path.suffix or path.exists()}
    for cfg in tournaments.values():
        cfg_path = cfg.path.resolve()
        if (
            cfg_path in resolved_candidates
            or cfg_path.name == candidate_path.name
            or cfg_path.stem == candidate_path.stem
        ):
            return cfg

    available = ", ".join(sorted(tournaments.keys()))
    raise ConfigError(
        _format_error(
            base_dir / "tournaments",
            "name",
            f"Tournament '{name}' not found. Available: {available or 'none'}",
        )
    )
