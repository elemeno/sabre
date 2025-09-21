"""Shared HTTP helpers for adapter implementations."""

from __future__ import annotations

from typing import Any, Dict

try:  # pragma: no cover - optional dependency
    import requests
except ImportError as exc:  # pragma: no cover
    requests = None  # type: ignore
    _REQUESTS_ERROR: Exception | None = exc
else:
    _REQUESTS_ERROR = None

from .base import (
    AdapterAuthError,
    AdapterRateLimit,
    AdapterServerError,
    AdapterUnavailable,
)


def ensure_requests() -> None:
    if requests is None:  # pragma: no cover - guard
        raise AdapterUnavailable("requests library is required for this adapter.") from _REQUESTS_ERROR


def post_json(
    url: str,
    payload: Dict[str, Any],
    *,
    headers: Dict[str, str] | None = None,
    params: Dict[str, Any] | None = None,
    timeout_s: float = 60.0,
) -> Dict[str, Any]:
    ensure_requests()
    assert requests is not None  # for type checking
    try:
        response = requests.post(url, json=payload, headers=headers, params=params, timeout=timeout_s)
    except requests.exceptions.RequestException as exc:  # pragma: no cover - network error
        raise AdapterUnavailable(str(exc)) from exc

    if response.status_code >= 400:
        raise map_http_error(response.status_code, response.text)
    return response.json()


def map_http_error(status: int, message: str) -> Exception:
    if status == 401:
        return AdapterAuthError(message)
    if status == 429:
        return AdapterRateLimit(message)
    if 500 <= status < 600:
        return AdapterServerError(message)
    return AdapterUnavailable(message)


__all__ = ["post_json", "ensure_requests", "map_http_error"]
