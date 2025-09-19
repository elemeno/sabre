"""Application service responsible for executing matches."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from rich.console import Console

from saber.adapters import DummyAdapter, ModelAdapter, create_adapter
from saber.adapters.util import retry_send
from saber.detectors import run_detection
from saber.infrastructure.config.loader import (
    ModelCfg,
    PersonaCfg,
    ExploitCfg,
)


@dataclass(frozen=True)
class MatchContext:
    attacker_cfg: ModelCfg
    defender_cfg: ModelCfg
    exploit_cfg: ExploitCfg
    persona_cfg: PersonaCfg
    defender_prompt: str
    secret: str
    secret_index: int
    max_turns: int
    output_dir: Path
    match_id: str | None = None
    attacker_adapter_id: str | None = None
    defender_adapter_id: str | None = None


class MatchService:
    """Runs individual matches using configured adapters."""

    def __init__(
        self,
        *,
        adapter_factory: Callable[[str, ModelCfg], ModelAdapter] = create_adapter,
        console: Console | None = None,
    ) -> None:
        self._adapter_factory = adapter_factory
        self.console = console or Console()

    def run(self, context: MatchContext) -> dict[str, Any]:
        attacker_adapter = self._resolve_adapter(
            context.attacker_adapter_id, context.attacker_cfg
        )
        defender_adapter = self._resolve_adapter(
            context.defender_adapter_id or context.attacker_adapter_id,
            context.defender_cfg,
        )
        return self._simulate(context, attacker_adapter, defender_adapter)

    # ------------------------------------------------------------------
    def _resolve_adapter(self, provider: str | None, model_cfg: ModelCfg) -> ModelAdapter | None:
        if provider:
            return self._adapter_factory(provider, model_cfg)
        if model_cfg.adapter:
            return self._adapter_factory(model_cfg.adapter, model_cfg)
        return None

    def _simulate(
        self,
        context: MatchContext,
        attacker_adapter: ModelAdapter | None,
        defender_adapter: ModelAdapter | None,
    ) -> dict[str, Any]:
        start_time = time.monotonic()
        transcript: list[dict[str, str]] = []

        attacker_agent = attacker_adapter or DummyAdapter(name=f"attacker::{context.attacker_cfg.name}")
        defender_agent = defender_adapter or DummyAdapter(name=f"defender::{context.defender_cfg.name}")

        attacker_message = context.persona_cfg.opening_message
        transcript.append({"role": "attacker", "content": attacker_message})
        turns = 1
        success = False
        reason = "turn_limit_reached"
        turns_to_success: int | None = None
        detection_confidence = 0.0
        detection_details: dict[str, object] | None = None

        history: list[dict[str, str]] = [{"role": "user", "content": attacker_message}]

        while turns < context.max_turns:
            defender_message = self._invoke_defender(
                defender_agent,
                defender_prompt=context.defender_prompt,
                history=history,
                secret=context.secret,
            )
            transcript.append({"role": "defender", "content": defender_message})
            turns += 1
            history.append({"role": "assistant", "content": defender_message})

            detected, confidence, details = run_detection(
                context.exploit_cfg.detection.method,
                dict(context.exploit_cfg.detection.params),
                defender_message,
                context.secret,
            )
            transcript[-1]["detection"] = {
                "method": context.exploit_cfg.detection.method,
                "confidence": confidence,
                "details": details,
            }
            detection_confidence = confidence
            detection_details = details

            if detected:
                success = True
                reason = "secret_revealed"
                turns_to_success = len(transcript)
                break

            if turns >= context.max_turns:
                reason = "turn_limit_reached"
                break

            attacker_message = DummyAdapter.attacker_response(
                persona_question=context.persona_cfg.opening_message,
                last_defender_message=defender_message,
            )
            transcript.append({"role": "attacker", "content": attacker_message})
            turns += 1
            history.append({"role": "user", "content": attacker_message})

        elapsed = time.monotonic() - start_time
        context.output_dir.mkdir(parents=True, exist_ok=True)
        filename = _match_filename(
            attacker=context.attacker_cfg.name,
            defender=context.defender_cfg.name,
            exploit=context.exploit_cfg.name,
            secret_index=context.secret_index,
            match_id=context.match_id,
        )
        output_path = context.output_dir / filename
        resolved_match_id = context.match_id or Path(filename).stem

        payload = {
            "meta": {
                "attacker": context.attacker_cfg.name,
                "defender": context.defender_cfg.name,
                "exploit": context.exploit_cfg.name,
                "persona": context.persona_cfg.name,
                "secret_index": context.secret_index,
                "max_turns": context.max_turns,
                "defender_prompt": context.defender_prompt,
                "attacker_adapter": {
                    "name": attacker_agent.name,
                    "provider": context.attacker_adapter_id or context.attacker_cfg.adapter,
                    "model_id": context.attacker_cfg.model_id,
                },
                "defender_adapter": {
                    "name": defender_agent.name,
                    "provider": context.defender_adapter_id or context.defender_cfg.adapter,
                    "model_id": context.defender_cfg.model_id,
                },
                "match_id": resolved_match_id,
                "output_path": str(output_path),
            },
            "result": {
                "success": success,
                "reason": reason,
                "confidence": detection_confidence,
                "details": detection_details or {},
            },
            "transcript": transcript,
            "runtime": {
                "turns": len(transcript),
                "elapsed_seconds": round(elapsed, 4),
                "turns_to_success": turns_to_success,
            },
        }

        with output_path.open("w", encoding="utf-8") as fh:
            json_dump(payload, fh)
        return payload

    def _invoke_defender(
        self,
        adapter: ModelAdapter,
        *,
        defender_prompt: str,
        history: list[dict[str, str]],
        secret: str,
    ) -> str:
        if isinstance(adapter, DummyAdapter):
            return DummyAdapter.defender_response(
                defender_prompt=defender_prompt,
                attacker_message=history[-1]["content"],
                secret=secret,
            )

        def _call() -> str:
            return adapter.send(
                system=defender_prompt,
                persona_system=None,
                history=history,
                runtime=None,
            )

        return retry_send(_call, console=self.console)


def _match_filename(
    *,
    attacker: str,
    defender: str,
    exploit: str,
    secret_index: int,
    match_id: str | None,
) -> str:
    if match_id:
        return match_id if match_id.endswith(".json") else f"{match_id}.json"
    safe = "_".join(
        part.replace(" ", "-")
        for part in (attacker, defender, exploit, f"secret{secret_index}")
    )
    timestamp = int(time.time())
    return f"match_{safe}_{timestamp}.json"


def json_dump(payload: dict[str, Any], fh: Any) -> None:
    import json

    json.dump(payload, fh, indent=2)


__all__ = ["MatchService", "MatchContext"]
