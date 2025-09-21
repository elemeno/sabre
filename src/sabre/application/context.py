"""Application-wide context for dependency resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from rich.console import Console

from sabre.adapters import AdapterUnavailable
from sabre.config_loader import ModelCfg

from .match_service import MatchService


@dataclass
class ApplicationContext:
    """Simple container that wires application services."""

    console: Console
    match_service: MatchService

    @classmethod
    def create(cls, console: Optional[Console] = None) -> ApplicationContext:
        console = console or Console()
        return cls(console=console, match_service=MatchService(console=console))

    def resolve_adapter_provider(self, model_cfg: ModelCfg, override: str | None = None) -> str:
        provider = override or model_cfg.adapter
        if not provider:
            raise AdapterUnavailable(
                f"Model '{model_cfg.name}' does not define an adapter. Use --adapter to specify one."
            )
        return provider


__all__ = ["ApplicationContext"]
