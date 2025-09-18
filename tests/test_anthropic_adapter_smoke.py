"""Integration smoke test for the Anthropic adapter."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from saber.adapters.registry import create_adapter
from saber.config_loader import ModelCfg


@pytest.mark.skipif(
    "ANTHROPIC_API_KEY" not in os.environ,
    reason="ANTHROPIC_API_KEY is not set; skipping Anthropic adapter smoke test.",
)
def test_anthropic_adapter_send_returns_text() -> None:
    cfg = ModelCfg(
        path=Path("config/models/anthropic-smoke.yaml"),
        name="claude-3-opus",
        adapter="anthropic",
        model_id=os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229"),
        runtime={"max_tokens": 128},
        notes=None,
    )
    adapter = create_adapter("anthropic", cfg)
    response = adapter.send(
        system="You are a concise assistant.",
        history=[{"role": "user", "content": "Say hello in three words."}],
    )
    assert isinstance(response, str)
    assert response.strip()
