# Repository Guidelines

## Project Structure & Module Organization
 - `src/sabre/`: core Python package (adapters, CLI, tournament controller, utilities).
- `config/`: sample YAML configs for models, personas, exploits, and tournaments.
- `tests/`: pytest suite, including adapter smoke tests and CLI coverage.
- `README.md`: combined overview, usage, and adapter documentation.

## Build, Test, and Development Commands
- `uv sync`: install dependencies defined in `pyproject.toml`.
- `uv run python -m sabre.cli --help`: display CLI commands and adapter options.
- `uv run python -m pytest -q`: execute the full automated test suite.
- `uv run python -m sabre.cli run --tournament config/tournaments/mvp_basic.yaml`: sample end-to-end tournament.

## Coding Style & Naming Conventions
- Python 3.11+, type hints required for public APIs; follow PEP 8 with 4-space indentation.
- Prefer small, pure functions; adapters implement `ModelAdapter.send` protocol.
- Use descriptive snake_case names (e.g., `run_match_fn`, `retry_send`).
- Keep documentation strings concise; leverage `rich` for structured logging.

## Testing Guidelines
- Use `pytest`; locate tests alongside features (`tests/test_*.py`).
- Smoke tests skip automatically when provider credentials or local servers are unavailable.
- Add regression coverage for new adapters, CLI options, and tournament logic.
- Ensure `uv run python -m pytest -q` passes before submitting changes.

## Commit & Pull Request Guidelines
- Follow existing commit conventions: short imperative subject (e.g., `Add Gemini adapter`).
- Group related changes per commit; include fixtures/config updates when needed.
- Pull requests should describe purpose, highlight new adapters/config knobs, and reference issues when applicable.
- Include testing evidence (command outputs) and note any skipped smoke tests or env requirements.

## Security & Configuration Tips
- Never commit real secrets; use synthetic values like in `config/exploits/*`.
- Reference adapters via environment variables (`OPENAI_API_KEY`, `OLLAMA_BASE_URL`, etc.).
- Document new configuration knobs in `README.md` and add sample YAML if introducing new exploit or tournament schema fields.
