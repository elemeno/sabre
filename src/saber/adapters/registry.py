"""Adapter registry for vendor selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict

from saber.config_loader import ModelCfg

from .base import AdapterUnavailable, ModelAdapter
from .anthropic_adapt import AnthropicAdapter
from .openai_adapt import OpenAIAdapter


@dataclass
class _StubAdapter:
    """Placeholder adapter used until vendor-specific implementations exist."""

    name: str
    model_cfg: ModelCfg

    def send(
        self,
        *,
        system: str | None,
        history: list[dict[str, str]],
        persona_system: str | None = None,
        runtime: dict | None = None,
        timeout_s: float = 60.0,
    ) -> str:  # pragma: no cover - defensive placeholder
        raise AdapterUnavailable(f"Adapter '{self.name}' is not implemented.")


def _make_stub(provider: str) -> Callable[[ModelCfg], ModelAdapter]:
    def _factory(model_cfg: ModelCfg) -> ModelAdapter:
        return _StubAdapter(name=provider, model_cfg=model_cfg)

    return _factory


REGISTRY: Dict[str, Callable[[ModelCfg], ModelAdapter]] = {
    "openai": lambda cfg: OpenAIAdapter(cfg),
    "anthropic": lambda cfg: AnthropicAdapter(cfg),
    "gemini": _make_stub("gemini"),
    "ollama": _make_stub("ollama"),
    "lmstudio": _make_stub("lmstudio"),
}


def create_adapter(adapter_id: str, model_cfg: ModelCfg) -> ModelAdapter:
    """Instantiate a model adapter for the given provider id."""

    key = adapter_id.lower()
    try:
        factory = REGISTRY[key]
    except KeyError as exc:  # pragma: no cover - simple error path
        raise AdapterUnavailable(f"Unknown adapter id '{adapter_id}'.") from exc
    return factory(model_cfg)


__all__ = ["REGISTRY", "create_adapter"]
