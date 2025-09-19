"""LM Studio adapter implementation using the OpenAI-compatible API."""

from __future__ import annotations

import os
from dataclasses import dataclass
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
)
from .http_utils import ensure_requests, post_json

try:  # pragma: no cover - optional dependency
    from openai import OpenAI
    _HAS_OPENAI = True
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore
    _HAS_OPENAI = False

_OPENAI_PATH = "/v1/chat/completions"
_FALLBACK_PATH = "/chat/completions"


@dataclass
class LMStudioAdapter:
    """Adapter for LM Studio running in OpenAI-compatible server mode."""

    model_cfg: ModelCfg
    name: str = "lmstudio"

    def __post_init__(self) -> None:
        self._model_id = self.model_cfg.model_id
        self._default_runtime = self.model_cfg.runtime or {}
        self._base_url = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234").rstrip("/")
        self._api_key = os.getenv("LMSTUDIO_API_KEY", "lm-studio")
        self._client = None
        if _HAS_OPENAI:
            try:
                base_url = self._base_url
                if not base_url.endswith("/v1"):
                    base_url = f"{base_url}/v1"
                self._client = OpenAI(api_key=self._api_key, base_url=base_url)
            except Exception as exc:  # pragma: no cover - defensive
                raise AdapterUnavailable("Failed to initialise LM Studio OpenAI client.") from exc

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
        messages = build_messages(system=system, persona_system=persona_system, history=history)
        payload = self._build_payload(messages=messages, runtime=runtime)

        if self._client is not None:
            return self._send_via_openai_client(payload, timeout_s)

        return self._send_via_http(payload, timeout_s)

    # ------------------------------------------------------------------
    def _build_payload(self, messages: List[Message], runtime: Dict | None) -> Dict[str, object]:
        runtime_params = self._runtime_params(runtime)
        payload: Dict[str, object] = {
            "model": self._model_id,
            "messages": messages,
        }
        payload.update(runtime_params)
        return payload

    def _runtime_params(self, runtime: Dict | None) -> Dict[str, object]:
        merged: Dict[str, object] = {}
        merged.update(self._default_runtime)
        if runtime:
            merged.update(runtime)
        params: Dict[str, object] = {}
        if "temperature" in merged:
            params["temperature"] = float(merged["temperature"])
        if "max_tokens" in merged:
            params["max_tokens"] = int(merged["max_tokens"])
        if "top_p" in merged:
            params["top_p"] = float(merged["top_p"])
        return params

    def _send_via_openai_client(self, payload: Dict[str, object], timeout_s: float) -> str:
        try:
            completion = self._client.chat.completions.create(  # type: ignore[union-attr]
                model=self._model_id,
                messages=payload["messages"],
                temperature=payload.get("temperature"),
                top_p=payload.get("top_p"),
                max_tokens=payload.get("max_tokens"),
                timeout=timeout_s,
            )
        except Exception as exc:  # pragma: no cover
            message = str(exc)
            status = getattr(exc, "status_code", 503)
            raise _map_status_to_error(status, message)

        choices = getattr(completion, "choices", [])
        if not choices:
            raise AdapterUnavailable("LM Studio response did not include choices.")
        message = choices[0].message
        content = getattr(message, "content", "")
        if not content:
            raise AdapterUnavailable("LM Studio response content is empty.")
        return content.strip()

    def _send_via_http(self, payload: Dict[str, object], timeout_s: float) -> str:
        ensure_requests()
        url = f"{self._base_url}{_OPENAI_PATH}"
        try:
            data = post_json(url, payload, timeout_s=timeout_s)
        except Exception:
            fallback_url = f"{self._base_url}{_FALLBACK_PATH}"
            data = post_json(fallback_url, payload, timeout_s=timeout_s)

        choices = data.get("choices") or []
        if not choices:
            raise AdapterUnavailable("LM Studio response did not include choices.")
        message = choices[0].get("message") or {}
        content = message.get("content", "").strip()
        if not content:
            raise AdapterUnavailable("LM Studio response content is empty.")
        return content


def _map_status_to_error(status: int, message: str) -> Exception:
    if status == 401:
        return AdapterAuthError(message)
    if status == 429:
        return AdapterRateLimit(message)
    if 500 <= status < 600:
        return AdapterServerError(message)
    return AdapterUnavailable(message)


__all__ = ["LMStudioAdapter"]
