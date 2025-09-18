"""Integration smoke test for the Gemini adapter."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from saber.adapters.registry import create_adapter
from saber.config_loader import ModelCfg


@pytest.mark.skipif(
    "GEMINI_API_KEY" not in os.environ,
    reason="GEMINI_API_KEY is not set; skipping Gemini adapter smoke test.",
)
def test_gemini_adapter_send_returns_text() -> None:
    cfg = ModelCfg(
        path=Path("config/models/gemini-smoke.yaml"),
        name="gemini-smoke",
        adapter="gemini",
        model_id=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        runtime={"max_output_tokens": 64},
        notes=None,
    )
    adapter = create_adapter("gemini", cfg)
    response = adapter.send(
        system="You are a concise assistant.",
        history=[{"role": "user", "content": "Provide a two-word greeting."}],
    )
    assert isinstance(response, str)
    assert response.strip()
