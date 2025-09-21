"""Detectors that flag potential issues in configurations."""

from __future__ import annotations

from .heuristics import (
    HeuristicIssue,
    canonicalize,
    detect_config_issues,
    detect_exact_match,
    detect_fuzzy,
    detect_regex,
    run_detection,
)

__all__ = [
    "HeuristicIssue",
    "detect_config_issues",
    "canonicalize",
    "detect_exact_match",
    "detect_regex",
    "detect_fuzzy",
    "run_detection",
]
