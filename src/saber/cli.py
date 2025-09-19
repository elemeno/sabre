"""Backward-compatible CLI entrypoint."""

from __future__ import annotations

from .interfaces.cli.app import app, main  # re-export

__all__ = ["app", "main"]

if __name__ == "__main__":  # pragma: no cover
    main()
