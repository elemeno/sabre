"""Compatibility wrapper."""

from __future__ import annotations

from saber.infrastructure.adapters import gemini_adapt as _module  # type: ignore
from saber.infrastructure.adapters.gemini_adapt import *  # noqa: F401,F403
