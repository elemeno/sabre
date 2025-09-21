"""Backward-compatible CLI entrypoint."""

from __future__ import annotations

import pathlib
import sys

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from .interfaces.cli.app import app, main  # re-export

__all__ = ["app", "main"]

if __name__ == "__main__":  # pragma: no cover
    main()
