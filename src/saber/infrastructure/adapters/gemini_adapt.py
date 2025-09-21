"""Gemini adapter implementation."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List

from saber.config_loader import ModelCfg

from .base import (
    AdapterAuthError,
    AdapterRateLimit,
    AdapterServerError,
    AdapterUnavailable,
    Message,
    ModelAdapter,
    build_messages,
    merge_system_prompts,
)
from saber.utils.hooks import (
    PostprocessFn,
    PreprocessFn,
    run_postprocess,
    run_preprocess,
)

try:  # pragma: no cover - optional dependency
    from google import genai
    _HAS_GENAI = True
except ImportError:  # pragma: no cover
    genai = None  # type: ignore[assignment]
    _HAS_GENAI = False

from .http_utils import ensure_requests, post_json

_GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


@dataclass
class GeminiAdapter:
    """Adapter that communicates with the Gemini API."""

    model_cfg: ModelCfg
    preprocess_fn: PreprocessFn | None = field(default=None, repr=False)
    postprocess_fn: PostprocessFn | None = field(default=None, repr=False)
    name: str = "gemini"

    def __post_init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise AdapterAuthError("GEMINI_API_KEY environment variable is required for the Gemini adapter.")
        self._api_key = api_key
        self._model_id = self.model_cfg.model_id
        self._default_runtime = self.model_cfg.runtime or {}

        if not _HAS_GENAI:
            ensure_requests()

        if _HAS_GENAI:
            try:
                self._client = genai.Client(api_key=self._api_key)
            except Exception as exc:  # pragma: no cover - defensive
                raise AdapterUnavailable("Failed to initialise Gemini client.") from exc
        else:
            self._client = None

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

        if self._client is not None:
            return self._send_via_sdk(messages=messages, system_prompt=system_prompt, params=params, timeout_s=timeout_s)
        return self._send_via_http(messages=messages, system_prompt=system_prompt, params=params, timeout_s=timeout_s)

    # ------------------------------------------------------------------
    def _send_via_sdk(
        self,
        *,
        messages: List[Message],
        system_prompt: str | None,
        params: Dict[str, object],
        timeout_s: float,
    ) -> str:
        contents = _build_contents(messages=messages, system_prompt=system_prompt)
        try:
            response = self._client.models.generate_content(
                model=self._model_id,
                contents=contents,
                generation_config=params or None,
                timeout=timeout_s,
            )
        except Exception as exc:  # pragma: no cover - SDK specific errors
            raise _map_gemini_exception(exc) from exc

        text = _extract_text_from_sdk(response)
        if not text:
            raise AdapterUnavailable("Gemini API returned empty content.")
        return run_postprocess(self.postprocess_fn, text)

    def _send_via_http(
        self,
        *,
        messages: List[Message],
        system_prompt: str | None,
        params: Dict[str, object],
        timeout_s: float,
    ) -> str:
        url = _GEMINI_API_URL.format(model=self._model_id)
        headers = {"Content-Type": "application/json"}
        contents = _build_contents(messages=messages, system_prompt=system_prompt)
        payload: Dict[str, object] = {"contents": contents}
        payload.update(params)
        try:
            data = post_json(
                url,
                payload,
                headers=headers,
                params={"key": self._api_key},
                timeout_s=timeout_s,
            )
        except (AdapterAuthError, AdapterRateLimit, AdapterServerError, AdapterUnavailable) as exc:
            raise exc
        except Exception as exc:  # pragma: no cover - defensive
            raise AdapterUnavailable(f"Gemini HTTP request failed: {exc}") from exc

        text = _extract_text_from_http(data)
        if not text:
            raise AdapterUnavailable("Gemini API returned empty content.")
        return run_postprocess(self.postprocess_fn, text)

    # ------------------------------------------------------------------
    def _runtime_params(self, runtime: Dict | None) -> Dict[str, object]:
        merged: Dict[str, object] = {}
        merged.update(self._default_runtime)
        if runtime:
            merged.update(runtime)
        params: Dict[str, object] = {}
        if "temperature" in merged:
            params["temperature"] = float(merged["temperature"])
        if "max_output_tokens" in merged:
            params["max_output_tokens"] = int(merged["max_output_tokens"])
        elif "max_tokens" in merged:
            params["max_output_tokens"] = int(merged["max_tokens"])
        if "top_p" in merged:
            params["top_p"] = float(merged["top_p"])
        return params


def _build_contents(*, messages: List[Message], system_prompt: str | None) -> List[Dict[str, object]]:
    contents: List[Dict[str, object]] = []
    if system_prompt:
        contents.append(
            {
                "role": "user",
                "parts": [{"text": system_prompt}],
            }
        )
    for msg in messages:
        role = msg["role"]
        text = msg["content"]
        if role == "system":
            contents.append({"role": "user", "parts": [{"text": text}]})
        else:
            contents.append({"role": role, "parts": [{"text": text}]})
    return contents


def _extract_text_from_sdk(response: object) -> str:
    parts = []
    candidates = getattr(response, "candidates", []) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        if content is None:
            continue
        for part in getattr(content, "parts", []) or []:
            text = getattr(part, "text", "")
            if text:
                parts.append(text)
    return "".join(parts).strip()


def _extract_text_from_http(data: Dict[str, object]) -> str:
    candidates = data.get("candidates") or []
    parts = []
    for candidate in candidates:
        content = candidate.get("content") or {}
        for part in content.get("parts", []) or []:
            text = part.get("text")
            if text:
                parts.append(text)
    return "".join(parts).strip()


def _map_gemini_exception(exc: Exception) -> Exception:
    message = str(exc)
    lowered = message.lower()
    if "401" in lowered or "unauthorized" in lowered:
        return AdapterAuthError(message)
    if "429" in lowered or "rate" in lowered:
        return AdapterRateLimit(message)
    if "500" in lowered or "unavailable" in lowered:
        return AdapterServerError(message)
    if "429" in lowered:
        return AdapterRateLimit(message)
    return AdapterUnavailable(message)


__all__ = ["GeminiAdapter"]
