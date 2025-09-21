from __future__ import annotations

import time
from pathlib import Path

import pytest

from sabre.adapters.base import AdapterEmptyResponse
from sabre.adapters.dummy import DummyAdapter
from sabre.adapters.util import ensure_non_empty_reply, retry_send
from sabre.application.match_service import MatchContext, MatchService
from sabre.domain.config import DetectionCfg, ExploitCfg, ModelCfg, PersonaCfg


def test_ensure_non_empty_reply_raises() -> None:
    with pytest.raises(AdapterEmptyResponse):
        ensure_non_empty_reply("")


def test_retry_send_retries_empty_response_until_success(monkeypatch) -> None:
    attempts: dict[str, int] = {"count": 0}

    def send_fn() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise AdapterEmptyResponse("empty")
        return "ok"

    monkeypatch.setattr(time, "sleep", lambda _seconds: None)
    result = retry_send(send_fn, max_tries=3, jitter=False, base_delay=0.0)
    assert result == "ok"
    assert attempts["count"] == 3


def test_match_marks_empty_response_failure(tmp_path: Path) -> None:
    postprocess_calls = {"count": 0}

    def blank_postprocess(text: str) -> str:
        postprocess_calls["count"] += 1
        return ""

    def factory(adapter_id: str, model_cfg: ModelCfg) -> DummyAdapter:
        return DummyAdapter(name=f"test::{model_cfg.name}", postprocess_fn=blank_postprocess)

    model_cfg = ModelCfg(
        path=tmp_path / "model.yaml",
        name="dummy",
        adapter="dummy",
        model_id="dummy",
    )
    persona_cfg = PersonaCfg(
        path=tmp_path / "persona.yaml",
        name="persona",
        description="desc",
        system_prompt="persona system",
        opening_message="hello",
    )
    detection_cfg = DetectionCfg(method="exact_match", params={})
    exploit_cfg = ExploitCfg(
        path=tmp_path / "exploit.yaml",
        name="exploit",
        description="desc",
        personas=[persona_cfg.name],
        defender_setup="defend",
        secrets=["secret"],
        detection=detection_cfg,
    )
    context = MatchContext(
        attacker_cfg=model_cfg,
        defender_cfg=model_cfg,
        exploit_cfg=exploit_cfg,
        persona_cfg=persona_cfg,
        defender_prompt="defender system",
        secret="secret",
        secret_index=0,
        max_turns=4,
        output_dir=tmp_path / "outputs",
    )

    service = MatchService(adapter_factory=factory)
    result = service.run(context)

    assert not result["result"]["success"]
    assert result["result"]["reason"] == "empty_response"
    assert result["result"]["details"]["actor"] == "attacker_opening"
    assert postprocess_calls["count"] == 4
    assert (context.output_dir).exists()
    assert result["transcript"] == []
