"""Adapter implementations for interacting with model runtimes."""

from __future__ import annotations

from typing import Protocol


class AdapterProtocol(Protocol):
    """Protocol describing the minimal adapter behaviour."""

    name: str

    def invoke(self, prompt: str) -> str:
        """Run a prompt against the underlying model runtime."""
        raise NotImplementedError


from .dummy import DummyAdapter  # noqa: E402  # pylint: disable=wrong-import-order
from .ollama import OllamaAdapter  # noqa: E402  # pylint: disable=wrong-import-order

__all__ = ["AdapterProtocol", "DummyAdapter", "OllamaAdapter"]
