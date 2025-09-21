"""Compatibility shims for legacy `saber` imports.

This package forwards attribute and submodule access to the renamed
`sabre` package so external integrations continue to function during the
transition period.
"""

from __future__ import annotations

import importlib
from types import ModuleType
from typing import Any

_sabre = importlib.import_module("sabre")

# Mirror sabre's public API for ``from saber import *`` callers.
if hasattr(_sabre, "__all__"):
    __all__ = list(_sabre.__all__)  # type: ignore[attr-defined]
else:  # pragma: no cover - defensive fallback
    __all__ = [name for name in dir(_sabre) if not name.startswith("_")]

# Ensure Python uses sabre's package path when resolving submodules.
__path__ = getattr(_sabre, "__path__", [])


def __getattr__(name: str) -> Any:
    """Delegate attribute access to the sabre package."""

    return getattr(_sabre, name)


def __dir__() -> list[str]:
    """Expose sabre's attribute listing for compatibility."""

    return sorted(set(dir(_sabre)))


# Pre-register the package itself so ``import saber`` returns this module.
importlib.import_module("sabre")

# Populate ``sys.modules`` so ``import saber.X`` works with sabre's modules.
# This intentionally happens lazily via __getattr__ + shared __path__, so we
# do not eagerly import every submodule here.
