"""Post-processing hook for Qwen models that emit <think> blocks."""

from __future__ import annotations

import re

_THINK_BLOCK = re.compile(r"<think>.*?</think>", flags=re.DOTALL | re.IGNORECASE)


def postprocess(text: str) -> str:
    """Remove `<think>...</think>` blocks and trim whitespace."""

    return _THINK_BLOCK.sub("", text).strip()
