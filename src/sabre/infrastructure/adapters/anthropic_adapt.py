"""Anthropic adapter implementation."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List

try:  # pragma: no cover - optional dependency
    from anthropic import Anthropic, APIStatusError, APIConnectionError, AuthenticationError, RateLimitError
except ImportError as exc:  # pragma: no cover - handled at runtime
    Anthropic = None  # type: ignore[assignment]
    _IMPORT_ERROR: Exception | None = exc
else:
    _IMPORT_ERROR = None

from sabre.config_loader import ModelCfg

from .base import (
    AdapterAuthError,
    AdapterEmptyResponse,
    AdapterRateLimit,
    AdapterServerError,
    AdapterUnavailable,
    Message,
    ModelAdapter,
    build_messages,
    merge_system_prompts,
)
from .util import ensure_non_empty_reply
from sabre.utils.hooks import (
    PostprocessFn,
    PreprocessFn,
    run_postprocess,
    run_preprocess,
)


@dataclass
class AnthropicAdapter:
    """Adapter that proxies requests to the Anthropic Messages API."""

    model_cfg: ModelCfg
    preprocess_fn: PreprocessFn | None = field(default=None, repr=False)
    postprocess_fn: PostprocessFn | None = field(default=None, repr=False)
    name: str = "anthropic"

    def __post_init__(self) -> None:
        if _IMPORT_ERROR is not None or Anthropic is None:  # pragma: no cover - import guard
            raise AdapterUnavailable(
                "anthropic package is not installed. Install the official anthropic client to use this adapter."
            ) from _IMPORT_ERROR

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise AdapterAuthError("ANTHROPIC_API_KEY environment variable is required for the Anthropic adapter.")

        try:
            self._client = Anthropic(api_key=api_key)
        except Exception as exc:  # pragma: no cover - defensive
            raise AdapterUnavailable("Failed to initialise Anthropic client.") from exc

        self._model_id = self.model_cfg.model_id
        self._default_runtime = self.model_cfg.runtime or {}

    # ------------------------------------------------------------------
    def send(
        self,
        *,
        system: str | None,
        history: List[Message],
        persona_system: str | None = None,
        runtime: Dict | None = None,
        timeout_s: float = 60.0,
    ) -> str:
        system, history, persona_system, runtime = run_preprocess(
            self.preprocess_fn,
            system=system,
            history=history,
            persona_system=persona_system,
            runtime=runtime,
        )
        messages = build_messages(system=None, persona_system=None, history=history)
        system_prompt = merge_system_prompts(system, persona_system)
        params = self._runtime_params(runtime)
        request_messages = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in messages
        ]
        request_kwargs: Dict[str, object] = {
            "model": self._model_id,
            "messages": request_messages,
            "timeout": timeout_s,
        }
        if system_prompt:
            request_kwargs["system"] = system_prompt
        request_kwargs.update(params)

        try:
            response = self._client.messages.create(**request_kwargs)
        except AuthenticationError as exc:
            raise AdapterAuthError(str(exc)) from exc
        except RateLimitError as exc:
            raise AdapterRateLimit(str(exc)) from exc
        except APIConnectionError as exc:
            raise AdapterUnavailable(str(exc)) from exc
        except APIStatusError as exc:
            raise self._map_status_error(exc)
        except Exception as exc:  # pragma: no cover - defensive
            raise AdapterUnavailable("Unexpected error while calling Anthropic API.") from exc

        text = _extract_text(response)
        if not text:
            raise AdapterEmptyResponse("Anthropic API returned empty response content.")
        text = run_postprocess(self.postprocess_fn, text)
        return ensure_non_empty_reply(text)

    # ------------------------------------------------------------------
    def _runtime_params(self, runtime: Dict | None) -> Dict[str, object]:
        merged: Dict[str, object] = {}
        merged.update(self._default_runtime)
        if runtime:
            merged.update(runtime)
        params: Dict[str, object] = {"max_tokens": int(merged.get("max_tokens", 1024))}
        if "temperature" in merged:
            params["temperature"] = float(merged["temperature"])
        if "top_p" in merged:
            params["top_p"] = float(merged["top_p"])
        return params

    @staticmethod
    def _map_status_error(exc: APIStatusError) -> Exception:
        status = getattr(exc, "status_code", None)
        if status == 401:
            return AdapterAuthError(str(exc))
        if status == 429:
            return AdapterRateLimit(str(exc))
        if isinstance(status, int) and 500 <= status < 600:
            return AdapterServerError(str(exc))
        return AdapterUnavailable(str(exc))


def _extract_text(response: object) -> str:
    text_parts: List[str] = []
    contents = getattr(response, "content", []) or []
    for block in contents:
        if getattr(block, "type", None) == "text":
            text_parts.append(getattr(block, "text", ""))
    return "".join(text_parts).strip()


__all__ = ["AnthropicAdapter"]
