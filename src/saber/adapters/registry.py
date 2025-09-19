"""Compatibility wrapper."""

from __future__ import annotations

from saber.infrastructure.adapters import registry as _module  # type: ignore
from saber.infrastructure.adapters.registry import *  # noqa: F401,F403
