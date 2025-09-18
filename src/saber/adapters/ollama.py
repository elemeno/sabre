"""Placeholder Ollama adapter for development environments."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OllamaAdapter:
    """Lightweight shim that documents how an Ollama adapter could behave."""

    model: str
    endpoint: str = "http://localhost:11434"
    name: str = "ollama"

    def invoke(self, prompt: str) -> str:
        """Return a simulated response showing the configured runtime."""
        preview = prompt.strip().splitlines()[0] if prompt.strip() else ""
        return (
            f"[{self.name} model={self.model} endpoint={self.endpoint}] "
            f"preview='{preview}'"
        )
