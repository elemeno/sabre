"""Adapter registry for vendor selection."""

from __future__ import annotations

from typing import Callable, Dict, Type

from sabre.config_loader import ModelCfg

from .anthropic_adapt import AnthropicAdapter
from .base import AdapterUnavailable, ModelAdapter
from .dummy import DummyAdapter
from .gemini_adapt import GeminiAdapter
from .lmstudio_adapt import LMStudioAdapter
from .ollama_adapt import OllamaAdapter
from .openai_adapt import OpenAIAdapter
from sabre.utils.hooks import attach_model_hooks


REGISTRY: Dict[str, Type[ModelAdapter]] = {
    "openai": OpenAIAdapter,
    "anthropic": AnthropicAdapter,
    "gemini": GeminiAdapter,
    "ollama": OllamaAdapter,
    "lmstudio": LMStudioAdapter,
    "dummy": DummyAdapter,
}


def create_adapter(adapter_id: str, model_cfg: ModelCfg) -> ModelAdapter:
    """Instantiate a model adapter for the given provider id."""

    key = adapter_id.lower()
    try:
        adapter_cls = REGISTRY[key]
    except KeyError as exc:  # pragma: no cover - simple error path
        raise AdapterUnavailable(f"Unknown adapter id '{adapter_id}'.") from exc

    preprocess_fn, postprocess_fn = attach_model_hooks(model_cfg)

    if adapter_cls is DummyAdapter:
        return adapter_cls(preprocess_fn=preprocess_fn, postprocess_fn=postprocess_fn)
    return adapter_cls(
        model_cfg,
        preprocess_fn=preprocess_fn,
        postprocess_fn=postprocess_fn,
    )


__all__ = ["REGISTRY", "create_adapter"]
