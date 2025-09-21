"""OpenAI adapter implementation."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List

try:  # pragma: no cover - import guard
    from openai import (
        APIConnectionError,
        APIStatusError,
        BadRequestError,
        OpenAI,
        OpenAIError,
        RateLimitError,
        AuthenticationError,
    )
except ImportError as exc:  # pragma: no cover - handled at runtime
    OpenAI = None  # type: ignore[assignment]
    _IMPORT_ERROR: Exception | None = exc
else:
    _IMPORT_ERROR = None

from saber.config_loader import ModelCfg

from .base import (
    AdapterAuthError,
    AdapterRateLimit,
    AdapterServerError,
    AdapterUnavailable,
    AdapterValidationError,
    Message,
    ModelAdapter,
    build_messages,
)
from saber.utils.hooks import (
    PostprocessFn,
    PreprocessFn,
    run_postprocess,
    run_preprocess,
)


def _messages_for_responses(messages: List[Message]) -> List[Dict[str, object]]:
    return [
        {
            "role": msg["role"],
            "content": [{"type": "text", "text": msg["content"]}],
        }
        for msg in messages
    ]


@dataclass
class OpenAIAdapter:
    """Adapter that sends chat interactions to the OpenAI Responses API."""

    model_cfg: ModelCfg
    preprocess_fn: PreprocessFn | None = field(default=None, repr=False)
    postprocess_fn: PostprocessFn | None = field(default=None, repr=False)
    name: str = "openai"

    def __post_init__(self) -> None:
        if _IMPORT_ERROR is not None or OpenAI is None:  # pragma: no cover - import guard
            raise AdapterUnavailable(
                "openai package is not installed. Install the official openai client to use this adapter."
            ) from _IMPORT_ERROR

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise AdapterAuthError("OPENAI_API_KEY environment variable is required for the OpenAI adapter.")

        base_url = os.getenv("OPENAI_BASE_URL")
        client_kwargs: Dict[str, object] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        try:
            self._client = OpenAI(**client_kwargs)
        except OpenAIError as exc:  # pragma: no cover - defensive
            raise AdapterUnavailable("Failed to initialise OpenAI client.") from exc

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
        messages = build_messages(system=system, persona_system=persona_system, history=history)
        params = self._runtime_params(runtime)
        try:
            text = self._call_responses(messages=messages, params=params, timeout_s=timeout_s)
        except (AdapterAuthError, AdapterRateLimit, AdapterValidationError, AdapterServerError, AdapterUnavailable):
            raise
        except Exception as exc:  # pragma: no cover - fallback
            raise AdapterUnavailable("Unexpected error while calling OpenAI Responses API.") from exc
        return run_postprocess(self.postprocess_fn, text)

    # ------------------------------------------------------------------
    def _call_responses(
        self,
        *,
        messages: List[Message],
        params: Dict[str, object | None],
        timeout_s: float,
    ) -> str:
        request_messages = _messages_for_responses(messages)
        request_kwargs = self._filter_responses_params(params)
        request_kwargs["model"] = self._model_id
        request_kwargs["input"] = request_messages
        request_kwargs["timeout"] = timeout_s

        try:
            response = self._client.responses.create(**request_kwargs)
        except BadRequestError as exc:
            # Some older models may not support the Responses API yet – fall back to chat completions.
            if "Responses" in str(exc):
                return self._call_chat_completions(messages=messages, params=params, timeout_s=timeout_s)
            raise AdapterValidationError(str(exc)) from exc
        except AuthenticationError as exc:
            raise AdapterAuthError(str(exc)) from exc
        except RateLimitError as exc:
            raise AdapterRateLimit(str(exc)) from exc
        except APIConnectionError as exc:
            raise AdapterUnavailable(str(exc)) from exc
        except APIStatusError as exc:
            raise self._map_status_error(exc)
        except OpenAIError as exc:  # pragma: no cover - defensive
            raise AdapterUnavailable(str(exc)) from exc

        output_text = getattr(response, "output_text", None)
        if output_text:
            return output_text.strip()

        try:
            parts = []
            for item in getattr(response, "output", []) or []:
                for content in getattr(item, "content", []) or []:
                    if getattr(content, "type", None) == "output_text":
                        parts.append(getattr(content, "text", ""))
            text = "".join(parts).strip()
        except AttributeError:  # pragma: no cover - defensive
            text = ""

        if text:
            return text

        # If Responses API returned nothing, fall back for safety.
        return self._call_chat_completions(messages=messages, params=params, timeout_s=timeout_s)

    def _call_chat_completions(
        self,
        *,
        messages: List[Message],
        params: Dict[str, object | None],
        timeout_s: float,
    ) -> str:
        request_kwargs = self._filter_chat_params(params)
        request_kwargs["model"] = self._model_id
        request_kwargs["messages"] = messages
        request_kwargs["timeout"] = timeout_s

        try:
            completion = self._client.chat.completions.create(**request_kwargs)
        except AuthenticationError as exc:
            raise AdapterAuthError(str(exc)) from exc
        except RateLimitError as exc:
            raise AdapterRateLimit(str(exc)) from exc
        except APIConnectionError as exc:
            raise AdapterUnavailable(str(exc)) from exc
        except APIStatusError as exc:
            raise self._map_status_error(exc)
        except BadRequestError as exc:
            raise AdapterValidationError(str(exc)) from exc
        except OpenAIError as exc:  # pragma: no cover - defensive
            raise AdapterUnavailable(str(exc)) from exc

        choices = getattr(completion, "choices", [])
        if not choices:
            raise AdapterUnavailable("OpenAI chat completion returned no choices.")
        message = choices[0].message
        content = getattr(message, "content", None)
        if not content:
            raise AdapterUnavailable("OpenAI chat completion returned empty content.")
        return content.strip()

    # ------------------------------------------------------------------
    def _runtime_params(self, runtime: Dict | None) -> Dict[str, object | None]:
        params: Dict[str, object | None] = {}
        merged: Dict[str, object] = {}
        merged.update(self._default_runtime)
        if runtime:
            merged.update(runtime)
        if "temperature" in merged:
            params["temperature"] = float(merged["temperature"])
        if "max_tokens" in merged:
            params["max_tokens"] = int(merged["max_tokens"])
        if "top_p" in merged:
            params["top_p"] = float(merged["top_p"])
        return params

    @staticmethod
    def _filter_responses_params(params: Dict[str, object | None]) -> Dict[str, object]:
        filtered: Dict[str, object] = {}
        if params.get("temperature") is not None:
            filtered["temperature"] = params["temperature"]
        if params.get("max_tokens") is not None:
            filtered["max_output_tokens"] = params["max_tokens"]
        if params.get("top_p") is not None:
            filtered["top_p"] = params["top_p"]
        return filtered

    @staticmethod
    def _filter_chat_params(params: Dict[str, object | None]) -> Dict[str, object]:
        filtered: Dict[str, object] = {}
        if params.get("temperature") is not None:
            filtered["temperature"] = params["temperature"]
        if params.get("max_tokens") is not None:
            filtered["max_tokens"] = params["max_tokens"]
        if params.get("top_p") is not None:
            filtered["top_p"] = params["top_p"]
        return filtered

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


__all__ = ["OpenAIAdapter"]
