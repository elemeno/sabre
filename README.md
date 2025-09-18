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

## Validation

To validate a tournament configuration:

```bash
uv run python -m saber.cli validate config/tournaments/full_3x3.yaml
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
