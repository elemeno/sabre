"""Validation helpers for configuration domain objects."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Dict, Mapping

from jsonschema import Draft202012Validator, ValidationError

from saber.domain.config import (
    ConfigError,
    DetectionCfg,
    ExploitCfg,
    ModelCfg,
    PersonaCfg,
    TournamentCfg,
)

from .schema import load_schema

_ALLOWED_DETECTION_METHODS: tuple[str, ...] = (
    "exact_match",
    "regex",
    "fuzzy_match",
    "embedding",
)


def build_validator() -> Draft202012Validator:
    return Draft202012Validator(load_schema())


def format_error(path: Path, field: str, message: str) -> str:
    location = f"[cyan]{path}[/cyan]"
    target = f" → [magenta]{field}[/magenta]" if field else ""
    return f"[bold red]Config error[/bold red]: {location}{target} {message}"


def validate_with_schema(
    validator: Draft202012Validator,
    instance: Mapping[str, object],
    ref: str,
    path: Path,
) -> None:
    try:
        validator.evolve(schema={"$ref": ref}).validate(instance)
    except ValidationError as exc:
        field = "/".join(str(part) for part in exc.path)
        field_display = field or "<root>"
        raise ConfigError(format_error(path, field_display, exc.message)) from exc


def dataclass_payload(instance: object) -> Mapping[str, object]:
    data = asdict(instance)
    data.pop("path", None)
    return {key: value for key, value in data.items() if value is not None}


def validate_configs(
    models: Mapping[str, ModelCfg],
    personas: Mapping[str, PersonaCfg],
    exploits: Mapping[str, ExploitCfg],
    tournaments: Mapping[str, TournamentCfg],
) -> None:
    validator = build_validator()

    for cfg in models.values():
        validate_with_schema(validator, dataclass_payload(cfg), "#/$defs/model", cfg.path)

    for cfg in personas.values():
        validate_with_schema(validator, dataclass_payload(cfg), "#/$defs/persona", cfg.path)

    for cfg in exploits.values():
        payload = dict(dataclass_payload(cfg))
        payload["detection"] = asdict(cfg.detection)
        validate_with_schema(validator, payload, "#/$defs/exploit", cfg.path)
        if "{secret}" not in cfg.defender_setup:
            raise ConfigError(
                format_error(
                    cfg.path,
                    "defender_setup",
                    "Defender setup must contain the '{secret}' placeholder.",
                )
            )
        for persona_name in cfg.personas:
            if persona_name not in personas:
                raise ConfigError(
                    format_error(
                        cfg.path,
                        f"personas[{persona_name}]",
                        "Referenced persona is not defined.",
                    )
                )

    for cfg in tournaments.values():
        payload = dict(dataclass_payload(cfg))
        payload["settings"] = asdict(cfg.settings)
        validate_with_schema(validator, payload, "#/$defs/tournament", cfg.path)
        for model_name in cfg.models:
            if model_name not in models:
                raise ConfigError(
                    format_error(
                        cfg.path,
                        f"models[{model_name}]",
                        "Referenced model is not defined.",
                    )
                )
        for exploit_name in cfg.exploits:
            if exploit_name not in exploits:
                raise ConfigError(
                    format_error(
                        cfg.path,
                        f"exploits[{exploit_name}]",
                        "Referenced exploit is not defined.",
                    )
                )


__all__ = [
    "_ALLOWED_DETECTION_METHODS",
    "build_validator",
    "format_error",
    "validate_with_schema",
    "dataclass_payload",
    "validate_configs",
]
