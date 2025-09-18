# Saber

Saber is a small toolkit for validating and running adversarial evaluation tournaments. It ships with a configurable CLI, JSON Schema validation for configs, and placeholder adapters/detectors that you can build on.

## Getting Started

Install dependencies with [uv](https://github.com/astral-sh/uv):

```bash
uv sync
```

Run the command line help to see available commands:

```bash
uv run python -m saber.cli --help
```

## CLI Examples

```bash
# Validate all configuration files under config/
saber validate --config-dir config/

# Inspect a tournament definition
saber show tournament "Full 3x3 Tournament"

# Run a deterministic dummy match and store the transcript
saber run-match \
  --attacker llama2-7b \
  --defender mistral-7b \
  --exploit secret_extraction \
  --persona direct_questioner \
  --secret-index 0 \
  --max-turns 6 \
  --output-dir results/dev

# Execute a full tournament schedule and compute summaries
saber run \
  --tournament "Full 3x3 Tournament" \
  --config-dir config/ \
  --output-dir results/full_3x3 \
  --seed 123
```

## Testing

```bash
uv run python -m pytest -q
```

## Project Layout

```
src/saber/        Python package (CLI, adapters, detectors, tournament controller)
config/           Sample configuration files used for validation demos
tests/            Automated tests
```
