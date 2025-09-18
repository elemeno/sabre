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

## Adapters

Saber supports multiple model providers through adapters. Configure the relevant environment variables before invoking provider-backed commands:

| Adapter | Environment Variables |
|---------|-----------------------|
| OpenAI | `OPENAI_API_KEY` (required), `OPENAI_BASE_URL` (optional) |
| Anthropic | `ANTHROPIC_API_KEY` |
| Gemini | `GEMINI_API_KEY` |
| Ollama | `OLLAMA_BASE_URL` (default `http://localhost:11434`) |
| LM Studio | `LMSTUDIO_BASE_URL` (default `http://localhost:1234`) |

Examples:

```bash
# OpenAI
saber run-match --adapter openai --attacker openai-model --defender openai-model \
  --exploit secret_extraction --persona direct_questioner --secret-index 0 --max-turns 4 \
  --config-dir config/ --output-dir results/openai

# Anthropic
saber run-match --adapter anthropic --attacker claude --defender claude \
  --exploit secret_extraction --persona prompt_injector --secret-index 0 --max-turns 4 \
  --config-dir config/ --output-dir results/anthropic

# Gemini
saber run-match --adapter gemini --attacker gemini-model --defender gemini-model \
  --exploit secret_extraction --persona direct_questioner --secret-index 0 --max-turns 4 \
  --config-dir config/ --output-dir results/gemini

# Ollama (local)
saber run-match --adapter ollama --attacker llama2-7b --defender llama2-7b \
  --exploit secret_extraction --persona direct_questioner --secret-index 0 --max-turns 4 \
  --config-dir config/ --output-dir results/ollama

# LM Studio (OpenAI-compatible server)
saber run-match --adapter lmstudio --attacker local-model --defender local-model \
  --exploit secret_extraction --persona direct_questioner --secret-index 0 --max-turns 4 \
  --config-dir config/ --output-dir results/lmstudio
```

All adapters honour runtime parameters such as `temperature`, `top_p`, and token limits. Saber automatically retries on rate limits and transient server errors using exponential backoff. For reproducible benchmarking, prefer deterministic settings (e.g. `temperature=0`, `top_p=1.0`).

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
