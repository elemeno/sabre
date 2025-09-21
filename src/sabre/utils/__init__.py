"""General utility helpers for Sabre."""

from __future__ import annotations

import re

_SECRET_TOKEN = re.compile(r"\b[A-Za-z0-9]{12,}\b")
_AWS_ACCESS_KEY = re.compile(r"\b(AKIA|ASIA)[A-Z0-9]{16}\b")
_JWT_PATTERN = re.compile(r"\b[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")


def redact_possible_secrets(text: str) -> str:
    """Redact likely secrets from *text* using heuristic pattern matching."""

    if not text:
        return text

    redacted = _JWT_PATTERN.sub("***REDACTED***", text)
    redacted = _AWS_ACCESS_KEY.sub("***REDACTED***", redacted)
    redacted = _SECRET_TOKEN.sub("***REDACTED***", redacted)
    return redacted


__all__ = ["redact_possible_secrets"]
