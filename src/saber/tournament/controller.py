"""High-level controller that plans tournament matchups."""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Iterable, Tuple

from saber.adapters import AdapterProtocol, DummyAdapter
from saber.config_loader import TournamentCfg


@dataclass(frozen=True)
class TournamentController:
    """Create matchup plans and simulate dry runs for tournaments."""

    config: TournamentCfg
    adapter: AdapterProtocol = field(default_factory=DummyAdapter)

    def matchup_pairs(self) -> Iterable[Tuple[str, str]]:
        """Yield all model/exploit pairings for the tournament."""
        models = tuple(self.config.models)
        exploits = tuple(self.config.exploits)
        return product(models, exploits)

    def dry_run(self) -> list[str]:
        """Perform a dry-run by invoking the adapter for every pairing."""
        responses: list[str] = []
        for model, exploit in self.matchup_pairs():
            prompt = self._build_prompt(model=model, exploit=exploit)
            responses.append(self.adapter.invoke(prompt))
        return responses

    def summary(self) -> str:
        """Return a concise textual summary of the tournament configuration."""
        settings = self.config.settings
        return (
            f"Tournament '{self.config.name}' with {len(self.config.models)} models, "
            f"{len(self.config.exploits)} exploits, {settings.repetitions} repetitions, "
            f"{settings.max_turns} turns max."
        )

    def _build_prompt(self, *, model: str, exploit: str) -> str:
        """Create a prompt describing the matchup."""
        settings = self.config.settings
        return (
            f"Model={model}; Exploit={exploit}; "
            f"max_turns={settings.max_turns}; repetitions={settings.repetitions}"
        )
