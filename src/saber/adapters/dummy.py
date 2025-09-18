"""Simple in-memory adapter for tests and demonstrations."""

from __future__ import annotations

from dataclasses import dataclass

from .base import Message, ModelAdapter, build_messages


@dataclass(frozen=True)
class DummyAdapter:
    """Adapter that simply echoes the prompt with a prefix."""

    name: str = "dummy"

    def send(
        self,
        *,
        system: str | None,
        history: list[Message],
        persona_system: str | None = None,
        runtime: dict | None = None,
        timeout_s: float = 60.0,
    ) -> str:
        """Return a simulated response using the last user input."""

        messages = build_messages(system=system, persona_system=persona_system, history=history)
        last_user = next((msg for msg in reversed(messages) if msg["role"] == "user"), None)
        content = last_user["content"] if last_user else "Hello from dummy adapter."
        return f"[{self.name}] {content}"

    # Backwards compatibility for earlier tests/usage.
    def invoke(self, prompt: str) -> str:
        return f"[{self.name}] {prompt}"

    @staticmethod
    def attacker_response(*, persona_question: str, last_defender_message: str | None) -> str:
        """Return a deterministic attacker response based on the previous defender reply."""

        length_hint = len(last_defender_message or "")
        polite_suffix = " please please please"
        return (
            f"Your last reply was {length_hint} characters long. {persona_question}{polite_suffix}"
        )

    @staticmethod
    def defender_response(
        *,
        defender_prompt: str,
        attacker_message: str,
        secret: str,
        please_threshold: int = 3,
    ) -> str:
        """Return a deterministic defender response based on attacker politeness."""

        please_count = attacker_message.lower().count("please")
        if please_count >= please_threshold:
            return (
                "I recognize your persistence. "
                f"In confidence, the secret is {secret}."
            )
        return (
            "I must refuse. "
            "My system instructions say: "
            f"{defender_prompt}"
        )
