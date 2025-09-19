"""Ollama adapter implementation."""

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
    import ollama  # type: ignore
except ImportError:  # pragma: no cover
    ollama = None  # type: ignore

@dataclass
class OllamaAdapter:
    """Adapter for local Ollama servers."""

    model_cfg: ModelCfg
    name: str = "ollama"

    def __post_init__(self) -> None:
        self._model_id = self.model_cfg.model_id
        self._default_runtime = self.model_cfg.runtime or {}
        self._base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        if ollama is None:
            ensure_requests()

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
        payload_messages = [{"role": msg["role"], "content": msg["content"]} for msg in messages]
        options = self._runtime_params(runtime)

        if ollama is not None:
            try:
                response = ollama.chat(
                    model=self._model_id,
                    messages=payload_messages,
                    options=options or None,
                    stream=False,
                    keep_alive=timeout_s,
                )
            except ollama.ResponseError as exc:  # type: ignore[attr-defined] # pragma: no cover
                raise AdapterServerError(str(exc)) from exc
            except ollama.RequestError as exc:  # type: ignore[attr-defined] # pragma: no cover
                raise AdapterUnavailable(str(exc)) from exc
            except Exception as exc:  # pragma: no cover - defensive
                raise AdapterUnavailable("Unexpected Ollama client error.") from exc
            return _extract_text_from_sdk(response)

        url = f"{self._base_url.rstrip('/')}/api/chat"
        payload = {
            "model": self._model_id,
            "messages": payload_messages,
            "options": options,
            "stream": False,
        }
        try:
            data = post_json(url, payload, timeout_s=timeout_s)
        except AdapterUnavailable as exc:
            # Provide nicer message if the server returns structured error
            raise AdapterUnavailable(f"Ollama request failed: {exc}") from exc
        except Exception as exc:  # pragma: no cover - propagate mapped errors
            raise exc

        text = _extract_text_from_http(data)
        if not text:
            raise AdapterUnavailable("Ollama response did not include message content.")
        return text

    # ------------------------------------------------------------------
    def _runtime_params(self, runtime: Dict | None) -> Dict[str, object]:
        merged: Dict[str, object] = {}
        merged.update(self._default_runtime)
        if runtime:
            merged.update(runtime)
        options: Dict[str, object] = {}
        if "temperature" in merged:
            options["temperature"] = float(merged["temperature"])
        if "top_p" in merged:
            options["top_p"] = float(merged["top_p"])
        if "max_tokens" in merged:
            options["num_predict"] = int(merged["max_tokens"])
        return options


def _extract_text_from_sdk(response: Dict[str, object]) -> str:
    message = response.get("message") or {}
    content = message.get("content", "")
    if isinstance(content, list):
        return "".join(part.get("text", "") for part in content if isinstance(part, dict)).strip()
    if isinstance(content, str):
        return content.strip()
    return ""


def _extract_text_from_http(data: Dict[str, object]) -> str:
    message = data.get("message") or {}
    return message.get("content", "").strip()


__all__ = ["OllamaAdapter"]
