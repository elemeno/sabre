"""Compatibility wrapper."""

from __future__ import annotations

from saber.infrastructure.adapters import anthropic_adapt as _module  # type: ignore
from saber.infrastructure.adapters.anthropic_adapt import *  # noqa: F401,F403
