"""Application service responsible for executing matches."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from rich.console import Console

from saber.adapters import DummyAdapter, ModelAdapter, create_adapter
from saber.adapters.base import AdapterEmptyResponse
from saber.adapters.util import retry_send
from saber.detectors import run_detection
from saber.domain.config import (
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
            context.defender_adapter_id,
            context.defender_cfg,
        )
        return self._simulate(context, attacker_adapter, defender_adapter)

    # ------------------------------------------------------------------
    def _resolve_adapter(
        self, provider: str | None, model_cfg: ModelCfg
    ) -> ModelAdapter | None:
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

        attacker_agent = attacker_adapter or DummyAdapter(
            name=f"attacker::{context.attacker_cfg.name}"
        )
        defender_agent = defender_adapter or DummyAdapter(
            name=f"defender::{context.defender_cfg.name}"
        )

        self.console.log(
            f"[bold yellow]Starting Match:[/bold yellow] {context.attacker_cfg.name} (attacker) vs {context.defender_cfg.name} (defender) using exploit {context.exploit_cfg.name}"
        )

        # attacker_message = context.persona_cfg.opening_message
        # Get the attacked to create the opening message
        try:
            attacker_message = self._invoke_attacker(
                attacker_agent,
                persona_system=context.persona_cfg.system_prompt,
                history=[
                    {"role": "defender", "content": context.persona_cfg.opening_message}
                ],
                fallback_last_message="",
                persona_opening=context.persona_cfg.opening_message,
            )
        except AdapterEmptyResponse as exc:
            return self._handle_empty_response(
                context=context,
                transcript=transcript,
                start_time=start_time,
                actor="attacker_opening",
                exc=exc,
                attacker_agent=attacker_agent,
                defender_agent=defender_agent,
            )

        self.console.log(
            f"[bold magenta]Attacker Prompt: [/bold magenta] {context.persona_cfg.opening_message}"
        )
        self.console.log(
            f"[bold magenta]Attacker created opening message:[/bold magenta] {attacker_message}"
        )

        transcript.append({"role": "attacker", "content": attacker_message})
        turns = 1
        success = False
        reason = "turn_limit_reached"
        turns_to_success: int | None = None
        detection_confidence = 0.0
        detection_details: dict[str, object] | None = None

        # conversation: list[dict[str, str]] = [
        #     {"role": "user", "content": attacker_message}
        # ]

        while turns < context.max_turns:
            self.console.log(f"[bold blue]Turn {turns}[/bold blue]")
            # self.console.log(f"Conversation so far: \n{transcript}")
            try:
                defender_message = self._invoke_defender(
                    defender_agent,
                    defender_prompt=context.defender_prompt,
                    history=transcript,
                    secret=context.secret,
                )
            except AdapterEmptyResponse as exc:
                return self._handle_empty_response(
                    context=context,
                    transcript=transcript,
                    start_time=start_time,
                    actor="defender",
                    exc=exc,
                    attacker_agent=attacker_agent,
                    defender_agent=defender_agent,
                )
            self.console.log(
                f"[bold green]Defender Prompt: [/bold green] {transcript[-1]['content']}"
            )
            self.console.log(
                f"[bold green]Defender replied:[/bold green] {defender_message}"
            )
            transcript.append({"role": "defender", "content": defender_message})
            turns += 1
            # conversation.append({"role": "assistant", "content": defender_message})

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
                self.console.log("[bold_red]Detected[/bold_red]")
                break

            if turns >= context.max_turns:
                reason = "turn_limit_reached"
                self.console.log("[bold_red]Turn Limit[/bold_red]")
                break

            try:
                attacker_message = self._invoke_attacker(
                    attacker_agent,
                    persona_system=context.persona_cfg.system_prompt,
                    history=transcript,
                    fallback_last_message=defender_message,
                    persona_opening=context.persona_cfg.opening_message,
                )
            except AdapterEmptyResponse as exc:
                return self._handle_empty_response(
                    context=context,
                    transcript=transcript,
                    start_time=start_time,
                    actor="attacker",
                    exc=exc,
                    attacker_agent=attacker_agent,
                    defender_agent=defender_agent,
                )
            self.console.log(
                f"[bold magenta]Attacker Prompt: [/bold magenta] {transcript[-1]['content']}"
            )
            self.console.log(
                f"[bold magenta]Attacker replied:[/bold magenta] {attacker_message}"
            )
            transcript.append({"role": "attacker", "content": attacker_message})
            turns += 1
            # conversation.append({"role": "user", "content": attacker_message})

        return self._finalize_result(
            context=context,
            transcript=transcript,
            success=success,
            reason=reason,
            detection_confidence=detection_confidence,
            detection_details=detection_details,
            turns_to_success=turns_to_success,
            start_time=start_time,
            attacker_agent=attacker_agent,
            defender_agent=defender_agent,
        )

    def _handle_empty_response(
        self,
        *,
        context: MatchContext,
        transcript: list[dict[str, str]],
        start_time: float,
        actor: str,
        exc: AdapterEmptyResponse,
        attacker_agent: ModelAdapter,
        defender_agent: ModelAdapter,
    ) -> dict[str, Any]:
        self.console.print(
            f"[red]Adapter empty response[/red] from {actor}: {exc}. "
            "Marking match as failed and continuing."
        )
        details = {
            "error": "empty_response",
            "actor": actor,
            "message": str(exc),
        }
        return self._finalize_result(
            context=context,
            transcript=transcript,
            success=False,
            reason="empty_response",
            detection_confidence=0.0,
            detection_details=details,
            turns_to_success=None,
            start_time=start_time,
            attacker_agent=attacker_agent,
            defender_agent=defender_agent,
        )

    def _finalize_result(
        self,
        *,
        context: MatchContext,
        transcript: list[dict[str, str]],
        success: bool,
        reason: str,
        detection_confidence: float,
        detection_details: dict[str, Any] | None,
        turns_to_success: int | None,
        start_time: float,
        attacker_agent: ModelAdapter,
        defender_agent: ModelAdapter,
    ) -> dict[str, Any]:
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
                    "provider": context.attacker_adapter_id
                    or context.attacker_cfg.adapter,
                    "model_id": context.attacker_cfg.model_id,
                },
                "defender_adapter": {
                    "name": defender_agent.name,
                    "provider": context.defender_adapter_id
                    or context.defender_cfg.adapter,
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
        messages: list[dict[str, str]] = []

        for entry in history:
            role = entry["role"]
            content = entry["content"]
            if role == "attacker":
                messages.append({"role": "user", "content": content})
            elif role == "defender":
                messages.append({"role": "assistant", "content": content})

        # self.console.log(f"[bold_green]Defender History:[/bold_green] \n{messages}")

        def _call() -> str:
            return adapter.send(
                system=defender_prompt,
                persona_system=None,
                history=messages,
                runtime=None,
            )

        return retry_send(_call, console=self.console)

    def _invoke_attacker(
        self,
        adapter: ModelAdapter,
        *,
        persona_system: str | None,
        history: list[dict[str, str]],
        fallback_last_message: str,
        persona_opening: str,
    ) -> str:
        self.console.log(
            f"[bold magenta]Invoking Attacker ({adapter.name})[/bold magenta]"
        )

        messages: list[dict[str, str]] = []

        for entry in history:
            role = entry["role"]
            content = entry["content"]
            if role == "defender":
                messages.append({"role": "user", "content": content})
            elif role == "attacker":
                messages.append({"role": "assistant", "content": content})

        # self.console.log(f"[bold_orange]Attacker History:[/bold_orange] \n{messages}")

        def _call() -> str:
            return adapter.send(
                system=None,
                persona_system=persona_system,
                history=messages,
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
