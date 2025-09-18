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
