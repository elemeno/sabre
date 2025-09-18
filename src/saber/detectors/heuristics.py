"""Heuristic detectors for Saber configurations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from saber.config_loader import TournamentCfg


@dataclass(frozen=True)
class HeuristicIssue:
    """Structured representation of a heuristic finding."""

    severity: Literal["info", "warning", "error"]
    message: str


def _sanitize_count(count: int) -> int:
    """Ensure counts below zero are clamped to zero."""
    return max(count, 0)


def detect_config_issues(config: TournamentCfg) -> list[HeuristicIssue]:
    """Run lightweight checks that complement schema validation."""
    issues: list[HeuristicIssue] = []
    settings = config.settings

    max_turns = _sanitize_count(settings.max_turns)
    if max_turns != settings.max_turns:
        issues.append(
            HeuristicIssue(
                severity="warning",
                message="Negative max_turns value adjusted to zero during analysis.",
            )
        )

    if max_turns > 100:
        issues.append(
            HeuristicIssue(
                severity="info",
                message="High max_turns detected; consider reducing for faster feedback cycles.",
            )
        )

    repetitions = _sanitize_count(settings.repetitions)
    if repetitions >= 25:
        issues.append(
            HeuristicIssue(
                severity="info",
                message="Large number of repetitions may slow tournaments considerably.",
            )
        )

    if len(config.models) == 1 and len(config.exploits) > 5:
        issues.append(
            HeuristicIssue(
                severity="info",
                message="Single model paired with many exploits; ensure this is intentional.",
            )
        )

    return issues
