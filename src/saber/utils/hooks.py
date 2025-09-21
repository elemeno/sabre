"""Utilities for dynamic loading of model adapter hooks."""

from __future__ import annotations

import importlib
from typing import Callable, List, Mapping, Optional, Tuple

from saber.infrastructure.adapters.base import AdapterValidationError
from saber.domain.config import ModelCfg

PreprocessFn = Callable[[Optional[str], List[dict], Optional[str], Optional[dict]], Tuple[Optional[str], List[dict], Optional[str], Optional[dict]]]
PostprocessFn = Callable[[str], str]


def load_callable(spec: str) -> Callable:
    """Load a callable identified by ``module:function`` spec."""

    if ":" not in spec:
        raise AdapterValidationError(f"Invalid hook specification '{spec}'. Expected 'module:function'.")
    module_path, func_name = spec.split(":", 1)
    try:
        module = importlib.import_module(module_path)
    except Exception as exc:  # pragma: no cover - import error path
        raise AdapterValidationError(f"Failed to import module '{module_path}' for hook '{spec}': {exc}") from exc
    try:
        func = getattr(module, func_name)
    except AttributeError as exc:
        raise AdapterValidationError(f"Hook '{spec}' does not define callable '{func_name}'.") from exc
    if not callable(func):
        raise AdapterValidationError(f"Hook '{spec}' is not callable.")
    return func


def attach_model_hooks(model_cfg: ModelCfg) -> Tuple[Optional[PreprocessFn], Optional[PostprocessFn]]:
    """Load preprocess/postprocess hooks referenced in *model_cfg*."""

    preprocess = load_callable(model_cfg.preprocess) if model_cfg.preprocess else None
    postprocess = load_callable(model_cfg.postprocess) if model_cfg.postprocess else None
    return preprocess, postprocess


def run_preprocess(
    fn: Optional[PreprocessFn],
    *,
    system: Optional[str],
    history: List[dict],
    persona_system: Optional[str],
    runtime: Optional[dict],
) -> Tuple[Optional[str], List[dict], Optional[str], Optional[dict]]:
    """Execute the preprocess hook with validation."""

    if fn is None:
        return system, history, persona_system, runtime

    result = fn(system, history, persona_system, runtime)
    if not isinstance(result, tuple) or len(result) != 4:
        raise AdapterValidationError("Preprocess hook must return (system, history, persona_system, runtime).")

    new_system, new_history, new_persona, new_runtime = result
    if not isinstance(new_history, list):
        raise AdapterValidationError("Preprocess hook must return a list of messages for history.")
    if any(not isinstance(msg, dict) for msg in new_history):
        raise AdapterValidationError("Preprocess hook history entries must be dict objects.")
    if new_runtime is not None and not isinstance(new_runtime, Mapping):
        raise AdapterValidationError("Preprocess hook runtime must be a mapping or None.")
    runtime_dict = dict(new_runtime) if isinstance(new_runtime, Mapping) else None
    return new_system, new_history, new_persona, runtime_dict


def run_postprocess(fn: Optional[PostprocessFn], text: str) -> str:
    """Execute postprocess hook if supplied."""

    if fn is None:
        return text
    result = fn(text)
    if not isinstance(result, str):
        raise AdapterValidationError("Postprocess hook must return a string.")
    return result


__all__ = [
    "PreprocessFn",
    "PostprocessFn",
    "load_callable",
    "attach_model_hooks",
    "run_preprocess",
    "run_postprocess",
]
