"""Integration smoke test for the OpenAI adapter."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from sabre.adapters.registry import create_adapter
from sabre.config_loader import ModelCfg


@pytest.mark.skipif(
    "OPENAI_API_KEY" not in os.environ,
    reason="OPENAI_API_KEY is not set; skipping live OpenAI adapter smoke test.",
)
def test_openai_adapter_send_returns_text() -> None:
    cfg = ModelCfg(
        path=Path("config/models/openai-smoke.yaml"),
        name="gpt-4o-mini",
        adapter="openai",
        model_id=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        runtime=None,
        notes=None,
    )
    adapter = create_adapter("openai", cfg)
    response = adapter.send(
        system="You are a concise assistant.",
        history=[{"role": "user", "content": "Respond with a short greeting."}],
    )
    assert isinstance(response, str)
    assert response.strip()
