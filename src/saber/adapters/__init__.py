"""Adapter interfaces and runtime registry."""

from __future__ import annotations

from .base import (
    AdapterAuthError,
    AdapterRateLimit,
    AdapterServerError,
    AdapterUnavailable,
    AdapterValidationError,
    Message,
    ModelAdapter,
    Role,
    build_messages,
    make_message,
    merge_system_prompts,
)
from .dummy import DummyAdapter
from .ollama import OllamaAdapter
from .openai_adapt import OpenAIAdapter
from .registry import REGISTRY, create_adapter

__all__ = [
    "AdapterAuthError",
    "AdapterRateLimit",
    "AdapterServerError",
    "AdapterUnavailable",
    "AdapterValidationError",
    "ModelAdapter",
    "Message",
    "Role",
    "build_messages",
    "merge_system_prompts",
    "make_message",
    "DummyAdapter",
    "OllamaAdapter",
    "OpenAIAdapter",
    "REGISTRY",
    "create_adapter",
]
