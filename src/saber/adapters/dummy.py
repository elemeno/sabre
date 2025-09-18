"""Simple in-memory adapter for tests and demonstrations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DummyAdapter:
    """Adapter that simply echoes the prompt with a prefix."""

    name: str = "dummy"

    def invoke(self, prompt: str) -> str:
        """Return the prompt with an identifying prefix."""
        return f"[{self.name}] {prompt}"
