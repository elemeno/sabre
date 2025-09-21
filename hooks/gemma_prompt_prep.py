"""Pre-processing hook example tailored for Gemma style prompts."""

from __future__ import annotations

from typing import Optional

_DIRECTIVE = "Follow the above constraints exactly."


def preprocess(
    system: Optional[str],
    history: list[dict],
    persona_system: Optional[str],
    runtime: Optional[dict],
):
    """Append a Gemma-friendly directive to the system prompt if missing."""

    system_text = system or ""
    if not system_text.endswith(_DIRECTIVE):
        system_text = f"{system_text}\n{_DIRECTIVE}".strip()
    return system_text or None, history, persona_system, runtime
