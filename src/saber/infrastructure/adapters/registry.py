"""Adapter registry for vendor selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict

from saber.config_loader import ModelCfg

from .anthropic_adapt import AnthropicAdapter
from .base import AdapterUnavailable, ModelAdapter
from .dummy import DummyAdapter
from .gemini_adapt import GeminiAdapter
from .lmstudio_adapt import LMStudioAdapter
from .ollama_adapt import OllamaAdapter
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
    "gemini": lambda cfg: GeminiAdapter(cfg),
    "ollama": lambda cfg: OllamaAdapter(cfg),
    "lmstudio": lambda cfg: LMStudioAdapter(cfg),
    "dummy": lambda cfg: DummyAdapter(),
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
