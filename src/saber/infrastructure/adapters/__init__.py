"""Adapter interfaces and runtime registry."""

from __future__ import annotations

from .anthropic_adapt import AnthropicAdapter
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
from .gemini_adapt import GeminiAdapter
from .lmstudio_adapt import LMStudioAdapter
from .ollama_adapt import OllamaAdapter
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
    "LMStudioAdapter",
    "OpenAIAdapter",
    "AnthropicAdapter",
    "GeminiAdapter",
    "REGISTRY",
    "create_adapter",
]
