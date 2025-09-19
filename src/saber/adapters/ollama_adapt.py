"""Compatibility wrapper."""

from __future__ import annotations

from saber.infrastructure.adapters import ollama_adapt as _module  # type: ignore
from saber.infrastructure.adapters.ollama_adapt import *  # noqa: F401,F403
