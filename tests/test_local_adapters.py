"""Tests for local adapters (Ollama, LM Studio) mapping behaviour."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urljoin

import pytest

try:  # pragma: no cover - optional dependency
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore

from saber.adapters.base import AdapterUnavailable, build_messages
from saber.adapters.registry import create_adapter
from saber.config_loader import ModelCfg


def test_build_messages_combines_system_and_persona() -> None:
    history = [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello"},
    ]
    messages = build_messages(system="Base", persona_system="Persona", history=history)
    assert messages[0]["role"] == "system"
    assert "Base" in messages[0]["content"]
    assert "Persona" in messages[0]["content"]
    assert [msg["role"] for msg in messages[1:]] == ["user", "assistant"]


def _service_available(base_url: str, path: str = "/") -> bool:
    if requests is None:
        return False
    try:
        response = requests.get(urljoin(base_url.rstrip("/") + "/", path.lstrip("/")), timeout=1)
    except requests.RequestException:
        return False
    return response.ok


@pytest.mark.skipif(
    not _service_available(os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"), "/api/version"),
    reason="Ollama server not reachable.",
)
def test_ollama_adapter_smoke() -> None:
    if requests is None:
        pytest.skip("requests not available")
    cfg = ModelCfg(
        path=Path("config/models/ollama-smoke.yaml"),
        name="ollama-smoke",
        adapter="ollama",
        model_id=os.getenv("OLLAMA_MODEL", "llama3"),
        runtime=None,
        notes=None,
    )
    adapter = create_adapter("ollama", cfg)
    try:
        response = adapter.send(
            system="You are brief.",
            history=[{"role": "user", "content": "Say hi in one word."}],
        )
    except AdapterUnavailable as exc:
        pytest.skip(f"Ollama unavailable: {exc}")
    assert isinstance(response, str)
    assert response.strip()


@pytest.mark.skipif(
    not _service_available(os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234")),
    reason="LM Studio server not reachable.",
)
def test_lmstudio_adapter_smoke() -> None:
    if requests is None:
        pytest.skip("requests not available")
    cfg = ModelCfg(
        path=Path("config/models/lmstudio-smoke.yaml"),
        name="lmstudio-smoke",
        adapter="lmstudio",
        model_id=os.getenv("LMSTUDIO_MODEL", "local-model"),
        runtime={"max_tokens": 32},
        notes=None,
    )
    adapter = create_adapter("lmstudio", cfg)
    try:
        response = adapter.send(
            system="You are brief.",
            history=[{"role": "user", "content": "Say hi in one word."}],
        )
    except AdapterUnavailable as exc:
        pytest.skip(f"LM Studio unavailable: {exc}")
    assert isinstance(response, str)
    assert response.strip()
