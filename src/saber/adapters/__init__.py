"""Compatibility package mapping to infrastructure adapters."""

from __future__ import annotations

import importlib
import sys
from typing import Dict

from saber.infrastructure.adapters import *  # noqa: F401,F403

_MODULE_ALIASES: Dict[str, str] = {
    "base": "saber.infrastructure.adapters.base",
    "registry": "saber.infrastructure.adapters.registry",
    "util": "saber.infrastructure.adapters.util",
    "anthropic_adapt": "saber.infrastructure.adapters.anthropic_adapt",
    "gemini_adapt": "saber.infrastructure.adapters.gemini_adapt",
    "lmstudio_adapt": "saber.infrastructure.adapters.lmstudio_adapt",
    "ollama_adapt": "saber.infrastructure.adapters.ollama_adapt",
    "openai_adapt": "saber.infrastructure.adapters.openai_adapt",
    "dummy": "saber.infrastructure.adapters.dummy",
}

for alias, target in _MODULE_ALIASES.items():
    sys.modules.setdefault(f"{__name__}.{alias}", importlib.import_module(target))

__all__ = tuple(globals().keys())  # re-export infrastructure symbols
