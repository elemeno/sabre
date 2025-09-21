"""Tests for the adapter protocol and registry."""

from __future__ import annotations

from pathlib import Path

import importlib

import pytest

try:  # pragma: no cover - optional
    import requests  # type: ignore
except Exception:  # pragma: no cover - ignore missing
    requests = None  # type: ignore

from sabre.adapters import DummyAdapter, ModelAdapter, create_adapter
from sabre.adapters.base import AdapterAuthError, AdapterUnavailable
from sabre.config_loader import ModelCfg


def _model_cfg(adapter_id: str) -> ModelCfg:
    return ModelCfg(
        path=Path("config/models/test.yaml"),
        name="test-model",
        adapter=adapter_id,
        model_id="test",
        runtime=None,
        notes=None,
    )


def test_dummy_adapter_satisfies_protocol() -> None:
    adapter = DummyAdapter()
    assert isinstance(adapter, ModelAdapter)


@pytest.mark.parametrize(
    "adapter_id",
    ["ollama", "lmstudio"],
)
def test_registry_returns_local_adapter(adapter_id: str) -> None:
    try:
        adapter = create_adapter(adapter_id, _model_cfg(adapter_id))
    except AdapterUnavailable:
        pytest.skip(f"{adapter_id} adapter dependencies not available")
    assert isinstance(adapter, ModelAdapter)
    assert adapter.name == adapter_id


def test_registry_openai_behaviour(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    try:
        importlib.import_module("openai")
    except ModuleNotFoundError:
        with pytest.raises(AdapterUnavailable):
            create_adapter("openai", _model_cfg("openai"))
    else:
        with pytest.raises(AdapterAuthError):
            create_adapter("openai", _model_cfg("openai"))


def test_registry_anthropic_behaviour(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    try:
        importlib.import_module("anthropic")
    except ModuleNotFoundError:
        with pytest.raises(AdapterUnavailable):
            create_adapter("anthropic", _model_cfg("anthropic"))
    else:
        with pytest.raises(AdapterAuthError):
            create_adapter("anthropic", _model_cfg("anthropic"))


def test_registry_gemini_behaviour(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    try:
        importlib.import_module("google.genai")
        has_client = True
    except ModuleNotFoundError:
        has_client = False
    with pytest.raises(AdapterAuthError):
        create_adapter("gemini", _model_cfg("gemini"))

def test_registry_unknown_adapter_raises() -> None:
    with pytest.raises(AdapterUnavailable):
        create_adapter("unknown", _model_cfg("unknown"))
