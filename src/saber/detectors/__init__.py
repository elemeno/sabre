"""Detectors that flag potential issues in configurations."""

from __future__ import annotations

from .heuristics import HeuristicIssue, detect_config_issues

__all__ = ["HeuristicIssue", "detect_config_issues"]
