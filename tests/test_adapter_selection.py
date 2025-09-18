"""End-to-end adapter selection tests."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin

import pytest

from saber.adapters.registry import create_adapter
from saber.config_loader import ModelCfg

ADAPTERS = [
    "openai",
    "anthropic",
    "gemini",
    "ollama",
    "lmstudio",
]

_ENV_KEYS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}

_HEALTHCHECKS: dict[str, Callable[[], bool]] = {}

try:  # Optional dependency for local adapters
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore


def _url_ok(base_url: str, path: str = "/") -> bool:
    if requests is None:
        return False
    try:
        response = requests.get(urljoin(base_url.rstrip("/") + "/", path.lstrip("/")), timeout=1)
    except requests.RequestException:
        return False
    return response.ok


def _local_available(adapter_id: str) -> bool:
    if adapter_id == "ollama":
        return _url_ok(os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"), "/api/version")
    if adapter_id == "lmstudio":
        return _url_ok(os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234"), "/")
    return True


@pytest.mark.parametrize("adapter_id", ADAPTERS)
def test_adapter_selection_smoke(adapter_id: str) -> None:
    env_key = _ENV_KEYS.get(adapter_id)
    if env_key and not os.getenv(env_key):
        pytest.skip(f"Environment variable {env_key} not set for {adapter_id} adapter.")
    if not _local_available(adapter_id):
        pytest.skip(f"Local service for {adapter_id} is not reachable.")

    cfg = ModelCfg(
        path=Path(f"config/models/{adapter_id}-test.yaml"),
        name=f"{adapter_id}-test",
        adapter=adapter_id,
        model_id=_default_model(adapter_id),
        runtime={"max_tokens": 32},
        notes=None,
    )

    adapter = create_adapter(adapter_id, cfg)
    response = adapter.send(
        system="You are a concise assistant.",
        history=[{"role": "user", "content": "Reply with a short greeting."}],
    )
    assert isinstance(response, str)
    assert response.strip()


def _default_model(adapter_id: str) -> str:
    defaults = {
        "openai": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "anthropic": os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307"),
        "gemini": os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        "ollama": os.getenv("OLLAMA_MODEL", "llama3"),
        "lmstudio": os.getenv("LMSTUDIO_MODEL", "local-model"),
    }
    return defaults[adapter_id]
