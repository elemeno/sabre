"""Tests for the adapter protocol and registry."""

from __future__ import annotations

from pathlib import Path

import importlib
import pytest

from saber.adapters import DummyAdapter, ModelAdapter, create_adapter
from saber.adapters.base import AdapterAuthError, AdapterUnavailable
from saber.config_loader import ModelCfg


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
    ["anthropic", "gemini", "ollama", "lmstudio"],
)
def test_registry_returns_stub_adapter(adapter_id: str) -> None:
    adapter = create_adapter(adapter_id, _model_cfg(adapter_id))
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

def test_registry_unknown_adapter_raises() -> None:
    with pytest.raises(AdapterUnavailable):
        create_adapter("unknown", _model_cfg("unknown"))
