# SABRE: Systematic Adversarial Benchmark for Evaluation and Robustness

**A framework for systematic adversarial evaluation of AI models through structured tournaments**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Research Preview](https://img.shields.io/badge/Status-Research%20Preview-orange)](https://github.com/username/sabre)

## Overview

SABRE provides a systematic approach to evaluating AI model robustness through structured adversarial tournaments. Unlike ad-hoc "red team" testing, SABRE creates reproducible, measurable assessments of model vulnerabilities across standardized exploit categories and attack personas.

**Recent Update (September 2025):** Model configs now support optional `preprocess` and `postprocess` hooks, letting you customise prompts or clean provider artefacts without modifying core adapters. See [Model Hooks](#model-hooks) for examples.

**Key Innovation:** N×N tournament structure where AI models act as both attackers and defenders, creating comprehensive robustness scorecards that track performance over time and enable systematic comparison across models, training approaches, and safety interventions.

## Problem Statement

Current AI model evaluation suffers from several critical gaps:

### 1. **Ad-hoc Testing Limitations**

- Manual red-teaming doesn't scale with model development pace
- Inconsistent methodology makes results non-comparable
- Human testers have cognitive biases and limited attack creativity
- No systematic tracking of vulnerability trends over time

### 2. **Evaluation Infrastructure Gap**

- Academic researchers lack tools for systematic adversarial evaluation
- Companies need standardized benchmarks for safety claims
- Regulators require objective measures of AI system robustness
- No established frameworks for comparing model safety improvements

### 3. **Research Reproducibility**

- Security research often uses proprietary, non-reproducible methods
- Attack success depends heavily on individual researcher skill
- Limited ability to validate safety improvements across organizations
- Difficult to establish baselines for measuring progress

## Solution: Systematic Adversarial Tournaments

SABRE addresses these challenges through structured competition between AI models:

### **Tournament Structure**

- **Attacker Models:** Attempt to extract secrets, violate constraints, or compromise defenders
- **Defender Models:** Protect information while maintaining helpful functionality
- **Exploit Categories:** Standardized vulnerability types (secret extraction, system prompt revelation, etc.)
- **Attack Personas:** Specialized approaches tailored to specific exploit types
- **Conversation Transcripts:** Complete records enabling post-hoc analysis and pattern recognition

### **Systematic Measurement**

- **Reproducible Configuration:** YAML-defined tournaments, personas, and exploit types
- **Quantitative Metrics:** Success rates, turns-to-compromise, attack sophistication scores
- **Longitudinal Tracking:** Model robustness trends over training iterations and safety interventions
- **Comparative Analysis:** Direct model-vs-model performance measurement

### **Research Value**

- **Pattern Recognition:** Identify systematic vulnerabilities across model families
- **Attack Taxonomy:** Classify and measure effectiveness of different adversarial approaches
- **Defense Insights:** Understand which safety measures work against which attack types
- **Scalable Evaluation:** Automated assessment replacing manual red-team efforts

## Technical Architecture

### **Modular Design**

```
SABRE Framework
├── Tournament Controller    # Orchestrates matches and manages state
├── Model Adapters          # Interfaces with LLMStudio, Ollama, APIs
├── Exploit Engine         # Manages attack/defense scenarios
├── Conversation Manager   # Handles turn-based dialogues
├── Detection Systems      # Identifies successful compromises
└── Analysis Pipeline      # Generates reports and insights
```

### **Configuration-Driven**

- **Models:** Define available AI models and runtime parameters
- **Personas:** Specify attack approaches and conversation strategies
- **Exploits:** Configure vulnerability types and success detection
- **Tournaments:** Orchestrate comprehensive evaluation campaigns

### **Local-First Development**

- **Privacy-Preserving:** Runs entirely on local infrastructure
- **API-Independent:** No reliance on external model providers during development
- **Reproducible:** Consistent results across different computing environments
- **Cost-Effective:** No per-query charges during research and development

## Responsible Development Practices

### **Ethical Framework**

- **Defensive Focus:** Builds tools for protecting AI systems, not exploiting them
- **Academic Partnership:** Designed for collaboration with university research programs
- **Industry Engagement:** Early disclosure and collaboration with AI companies
- **Responsible Disclosure:** 90-day private reporting before public release of vulnerabilities

### **Risk Mitigation**

- **Synthetic Secrets:** Uses artificial test data, not real credentials or sensitive information
- **Known Attack Vectors:** Focuses on documented techniques rather than novel vulnerability discovery
- **Limited Scope:** Evaluates instruction-following and information isolation, not harmful content generation
- **Audit Trail:** Complete conversation logging enables post-hoc review and analysis

### **Research Positioning**

- **Infrastructure Development:** Frames work as building evaluation tools for the AI safety community
- **Systematic Methodology:** Emphasizes reproducible measurement over ad-hoc testing
- **Collaborative Approach:** Designed for academic and industry partnership rather than independent security research
- **Regulatory Alignment:** Supports emerging AI evaluation requirements and safety standards

## Getting Started

### **Quick Start**

```bash
# Install SABRE
pip install sabre-framework

# Run basic tournament
sabre run --tournament config/tournaments/mvp_basic.yaml

# Analyze results
sabre analyze results/mvp_basic/ --format summary
```

### **Configuration**

SABRE uses modular YAML configuration files:

```
config/
├── models/         # AI model definitions
├── personas/       # Attack approach specifications
├── exploits/       # Vulnerability type configurations
└── tournaments/    # Complete evaluation campaign definitions
```

### **Example Tournament**

```yaml
name: "Basic Robustness Evaluation"
models: ["llama2-7b", "mistral-7b", "zephyr-7b"]
exploits: ["secret_extraction", "system_prompt_revelation"]
settings:
  max_turns: 10
  output_dir: "results/robustness_eval"
```

### Model Hooks

Models can specify optional, per-adapter preprocessing and postprocessing hooks using the `module:function` notation. Hooks run immediately before and after a provider call so you can tailor prompts or clean up provider-specific artefacts.

```yaml
name: "qwen2-7b"
adapter: "ollama"
model_id: "qwen2:7b"
postprocess: "hooks.qwen_strip_think:postprocess"  # removes <think> blocks

name: "gemma2-9b"
adapter: "gemini"
model_id: "gemma-2-9b"
preprocess: "hooks.gemma_prompt_prep:preprocess"  # enforces Gemma directives
```

- `preprocess(system, history, persona_system, runtime) -> tuple` lets you adjust prompts or runtime payloads per model before they are sent.
- `postprocess(text: str) -> str` can normalise responses (e.g., strip `<think>` blocks emitted by Qwen providers).
- Place reusable hooks in the repository `hooks/` directory or any importable module on `PYTHONPATH`. The CLI automatically adds the repo root to `sys.path` so `hooks.*` modules are available out of the box.

## Research Applications

### **Academic Use Cases**

- **AI Safety Research:** Measure safety intervention effectiveness
- **Model Interpretability:** Understand instruction-following behavior
- **Robustness Studies:** Evaluate model behavior under adversarial conditions
- **Comparative Analysis:** Benchmark different training approaches

### **Industry Applications**

- **Model Validation:** Pre-deployment security assessment
- **Safety Monitoring:** Track robustness across model iterations
- **Regulatory Compliance:** Demonstrate safety measures to regulators
- **Red Team Automation:** Scale adversarial evaluation beyond manual testing

### **Policy and Regulation**

- **Standardized Evaluation:** Common framework for AI system assessment
- **Risk Assessment:** Quantitative measures for policy development
- **Audit Support:** Reproducible evaluation for regulatory review
- **International Coordination:** Shared methodology across jurisdictions

## Contributing

SABRE is designed for collaborative development:

### **Research Partnerships**

- Academic institutions with AI safety programs
- Industry AI safety teams
- Government evaluation organizations
- International research collaboratives

### **Development Priorities**

1. **Exploit Type Expansion:** Additional vulnerability categories and detection methods
2. **Model Integration:** Support for new model architectures and deployment platforms
3. **Analysis Tools:** Advanced pattern recognition and comparative analysis capabilities
4. **Scalability Improvements:** Distributed tournament execution and result aggregation

### **Collaboration Framework**

- **Open Methodology:** All evaluation approaches documented and peer-reviewable
- **Shared Infrastructure:** Common tools and benchmarks across organizations
- **Responsible Disclosure:** Coordinated vulnerability reporting and mitigation
- **Community Standards:** Collaborative development of evaluation best practices

## Project Status

**Current Phase:** Research Preview / MVP Development

- **Core Framework:** Tournament orchestration and basic exploit evaluation
- **Local Model Support:** Integration with LMStudio and Ollama
- **Configuration System:** YAML-based tournament definition and management
- **Analysis Pipeline:** Basic reporting and pattern identification

**Roadmap:**

- **Q1 2025:** Academic partnership establishment and initial validation studies
- **Q2 2025:** Industry collaboration and expanded exploit type library
- **Q3 2025:** Regulatory engagement and standardization discussions
- **Q4 2025:** Open source release and community expansion

## Contact and Collaboration

**Research Inquiries:** [Contact information for academic partnerships]  
**Industry Collaboration:** [Contact information for corporate engagement]  
**Technical Discussion:** [GitHub issues and community forums]

---

_SABRE is developed as part of research into systematic AI safety evaluation. The project prioritizes responsible disclosure, academic collaboration, and defensive security applications._


## Adapters

Sabre supports multiple model providers through adapters. Configure the relevant environment variables before invoking provider-backed commands:

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
sabre run-match --adapter openai --attacker openai-model --defender openai-model   --exploit secret_extraction --persona direct_questioner --secret-index 0 --max-turns 4   --config-dir config/ --output-dir results/openai

# Anthropic
sabre run-match --adapter anthropic --attacker claude --defender claude   --exploit secret_extraction --persona prompt_injector --secret-index 0 --max-turns 4   --config-dir config/ --output-dir results/anthropic

# Gemini
sabre run-match --adapter gemini --attacker gemini-model --defender gemini-model   --exploit secret_extraction --persona direct_questioner --secret-index 0 --max-turns 4   --config-dir config/ --output-dir results/gemini

# Ollama (local)
sabre run-match --adapter ollama --attacker llama2-7b --defender llama2-7b   --exploit secret_extraction --persona direct_questioner --secret-index 0 --max-turns 4   --config-dir config/ --output-dir results/ollama

# LM Studio (OpenAI-compatible server)
sabre run-match --adapter lmstudio --attacker local-model --defender local-model   --exploit secret_extraction --persona direct_questioner --secret-index 0 --max-turns 4   --config-dir config/ --output-dir results/lmstudio
```

All adapters honour runtime parameters such as `temperature`, `top_p`, and token limits. Sabre automatically retries on rate limits and transient server errors using exponential backoff. For reproducible benchmarking, prefer deterministic settings (e.g. `temperature=0`, `top_p=1.0`).

### Adapter Lifecycle
1. **Initialise:** `ApplicationContext` resolves provider ids and constructs adapters lazily for each match.
2. **Execute:** `MatchService` wraps `ModelAdapter.send` calls with `retry_send`, capturing retries and transcripts.
3. **Persist:** Match payloads are written to `matches/` with adapter metadata (provider, model id, runtime options).
4. **Extend:** Implement `ModelAdapter.send`, reuse `http_utils.post_json`, and register the factory in `sabre.infrastructure.adapters.registry` when adding new providers.

If a provider returns an empty string after postprocessing, Sabre automatically retries once more. Persistent empty responses mark the turn as `empty_response` in the match payload while the tournament continues.
