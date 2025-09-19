# Architecture Improvement Recommendations

## Architectural Assessment Summary
- Modular adapter layer and configuration-driven tournaments are strong foundations.
- Architectural debt concentrates in oversized orchestration modules (`cli.py`, `tournament/controller.py`, `config_loader.py`).
- Boundaries between domain logic, application orchestration, and infrastructure are blurred, limiting composability and reuse.

## Key Improvement Areas
- **Decompose the CLI surface:** Split `cli.py` into command modules (`commands/run_match.py`, `commands/run_tournament.py`, etc.), isolating argument parsing from orchestration services. Expose a programmatic API layer so other agents can schedule tournaments without invoking Typer directly.
- **Refine tournament orchestration:** Separate scheduling, execution, persistence, and reporting concerns inside `TournamentController`. Introduce dedicated services (e.g., `MatchExecutor`, `SummaryAggregator`) injected via the controller to allow alternative execution strategies (async, distributed, dry-run).
- **Restructure configuration loading:** Convert `config_loader.py` into smaller units (`schema.py`, `loader.py`, `validators.py`). Consider Pydantic dataclasses or frozen `attrs` models to enforce validation closer to the domain and to enable richer defaults/versioning.
- **Unify adapter primitives:** Many providers implement similar HTTP flows. Extract shared request/response helpers (timeouts, JSON serialization, option filtering) into reusable utilities to reduce duplication and simplify future adapter additions.
- **Promote dependency inversion:** The CLI currently instantiates adapters directly. Introduce a lightweight service container/context that resolves adapters and persistence paths; pass this into command handlers and controllers to make unit testing easier.

## Recommended Next Steps
1. Establish a top-level package layout: `application/` (use cases, services), `domain/` (entities, schemas), `infrastructure/` (adapters, persistence), `interfaces/cli/` (Typer wiring).
2. Create a central `MatchService` that orchestrates adapter selection, retry behaviour, and transcript logging; reuse it across commands and tournament runs.
3. Add contract tests for the configuration layer to lock in expected schemas and provide confidence when refactoring into modular components.
4. Document the adapter lifecycle (initialisation, retries, teardown) so future contributors can extend providers without touching CLI internals.
