"""Placeholder Ollama adapter for development environments."""

from __future__ import annotations

from dataclasses import dataclass

from .base import Message, ModelAdapter, build_messages


@dataclass(frozen=True)
class OllamaAdapter:
    """Lightweight shim that documents how an Ollama adapter could behave."""

    model: str
    endpoint: str = "http://localhost:11434"
    name: str = "ollama"

    def send(
        self,
        *,
        system: str | None,
        history: list[Message],
        persona_system: str | None = None,
        runtime: dict | None = None,
        timeout_s: float = 60.0,
    ) -> str:
        """Return a simulated response showing the configured runtime."""

        messages = build_messages(system=system, persona_system=persona_system, history=history)
        preview = messages[-1]["content"] if messages else ""
        return (
            f"[{self.name} model={self.model} endpoint={self.endpoint}] "
            f"preview='{preview}'"
        )

    def invoke(self, prompt: str) -> str:
        return self.send(system=None, history=[{"role": "user", "content": prompt}])
