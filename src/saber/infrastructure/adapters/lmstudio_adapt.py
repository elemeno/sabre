"""LM Studio adapter implementation."""

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
from .http_utils import ensure_requests, map_http_error

_OPENAI_PATH = "/v1/chat/completions"
_FALLBACK_PATH = "/chat/completions"


@dataclass
class LMStudioAdapter:
    """Adapter for LM Studio in OpenAI-compatible server mode."""

    model_cfg: ModelCfg
    name: str = "lmstudio"

    def __post_init__(self) -> None:
        self._model_id = self.model_cfg.model_id
        self._default_runtime = self.model_cfg.runtime or {}
        self._base_url = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234")

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
        ensure_requests()
        import requests  # type: ignore  # noqa: WPS433
        messages = build_messages(system=system, persona_system=persona_system, history=history)
        payload = self._build_payload(messages=messages, runtime=runtime)

        response = self._post(_OPENAI_PATH, payload, timeout_s)
        if response is None:
            response = self._post(_FALLBACK_PATH, payload, timeout_s)
        if response is None:
            raise AdapterUnavailable("LM Studio API is unreachable. Ensure the server is running.")

        if response.status_code == 401:
            raise AdapterAuthError(response.text)
        if response.status_code == 429:
            raise AdapterRateLimit(response.text)
        if 500 <= response.status_code < 600:
            raise AdapterServerError(response.text)
        if not response.ok:
            raise AdapterUnavailable(response.text)

        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            raise AdapterUnavailable("LM Studio response did not include choices.")
        message = choices[0].get("message") or {}
        content = message.get("content", "").strip()
        if not content:
            raise AdapterUnavailable("LM Studio response content is empty.")
        return content

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

    def _post(self, path: str, payload: Dict[str, object], timeout_s: float):
        url = f"{self._base_url.rstrip('/')}{path}"
        if requests is None:  # pragma: no cover - guard
            return None
        import requests  # type: ignore  # noqa: WPS433

        try:
            response = requests.post(url, json=payload, timeout=timeout_s)
        except requests.exceptions.RequestException:
            return None
        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise map_http_error(response.status_code, response.text)
        return response


__all__ = ["LMStudioAdapter"]
