"""Adapter utility helpers."""

from __future__ import annotations

import random
import time
from typing import Callable, TypeVar

from rich.console import Console

from .base import (
    AdapterAuthError,
    AdapterEmptyResponse,
    AdapterRateLimit,
    AdapterServerError,
    AdapterUnavailable,
    AdapterValidationError,
)

T = TypeVar("T")


def retry_send(
    send_fn: Callable[[], T],
    *,
    max_tries: int = 4,
    base_delay: float = 0.5,
    jitter: bool = True,
    console: Console | None = None,
) -> T:
    """Retry wrapper for adapter send operations with exponential backoff."""

    console = console or Console()
    attempt = 0
    delay = base_delay

    while True:
        attempt += 1
        try:
            return send_fn()
        except AdapterAuthError:
            raise
        except AdapterValidationError:
            raise
        except AdapterEmptyResponse as exc:
            if attempt >= max_tries:
                raise
            _log_retry(console, attempt, max_tries, "empty response", exc)
        except AdapterRateLimit as exc:
            if attempt >= max_tries:
                raise
            _log_retry(console, attempt, max_tries, "rate limit", exc)
        except AdapterServerError as exc:
            if attempt >= max_tries:
                raise
            _log_retry(console, attempt, max_tries, "server error", exc)
        except AdapterUnavailable as exc:
            if attempt >= max_tries:
                raise
            _log_retry(console, attempt, max_tries, "adapter unavailable", exc)
        except Exception as exc:  # pragma: no cover - defensive
            if attempt >= max_tries:
                raise AdapterUnavailable("Unexpected adapter error.") from exc
            _log_retry(console, attempt, max_tries, "unexpected error", exc)

        sleep_time = delay
        if jitter:
            sleep_time *= 1 + random.random()
        time.sleep(sleep_time)
        delay *= 2


def _log_retry(console: Console, attempt: int, max_tries: int, reason: str, exc: Exception) -> None:
    console.print(
        f"[yellow]Adapter retry {attempt}/{max_tries} after {reason}: {exc}[/yellow]"
    )


def ensure_non_empty_reply(text: str) -> str:
    """Ensure *text* contains non-whitespace content, otherwise raise."""

    if text is None or not text.strip():
        raise AdapterEmptyResponse("Adapter returned empty response content.")
    return text


__all__ = ["retry_send", "ensure_non_empty_reply"]
