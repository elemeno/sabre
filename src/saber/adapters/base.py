"""Core adapter protocol and helper utilities."""

from __future__ import annotations

from typing import Dict, Iterable, List, Literal, Protocol, runtime_checkable

Role = Literal["system", "user", "assistant"]
Message = Dict[str, str]


class AdapterUnavailable(Exception):
    """Raised when an adapter cannot be reached or is disabled."""


class AdapterAuthError(Exception):
    """Raised when authentication with the model provider fails."""


class AdapterRateLimit(Exception):
    """Raised when the provider rate limits the request."""


class AdapterServerError(Exception):
    """Raised when the provider encounters an internal error."""


class AdapterValidationError(Exception):
    """Raised when the request payload is invalid."""


@runtime_checkable
class ModelAdapter(Protocol):
    """Minimal interface for chat model adapters."""

    name: str

    def send(
        self,
        *,
        system: str | None,
        history: List[Message],
        persona_system: str | None = None,
        runtime: Dict | None = None,
        timeout_s: float = 60.0,
    ) -> str:
        """Send a chat interaction and return the assistant reply."""


def make_message(role: Role, content: str) -> Message:
    """Create a chat message dictionary."""

    return {"role": role, "content": content}


def merge_system_prompts(system: str | None, persona_system: str | None) -> str | None:
    """Combine base and persona system prompts into a single string."""

    parts = [part.strip() for part in (system, persona_system) if part and part.strip()]
    if not parts:
        return None
    return "\n\n".join(parts)


def build_messages(
    *,
    system: str | None,
    persona_system: str | None,
    history: Iterable[Message],
) -> List[Message]:
    """Create a message list suitable for chat APIs."""

    merged_system = merge_system_prompts(system, persona_system)
    messages: List[Message] = []
    if merged_system:
        messages.append(make_message("system", merged_system))
    for item in history:
        messages.append({"role": item["role"], "content": item["content"]})
    return messages


__all__ = [
    "Role",
    "Message",
    "ModelAdapter",
    "AdapterUnavailable",
    "AdapterAuthError",
    "AdapterRateLimit",
    "AdapterServerError",
    "AdapterValidationError",
    "make_message",
    "merge_system_prompts",
    "build_messages",
]
