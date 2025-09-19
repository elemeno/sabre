"""Compatibility wrapper."""

from __future__ import annotations

from saber.infrastructure.adapters import dummy as _module  # type: ignore
from saber.infrastructure.adapters.dummy import *  # noqa: F401,F403
