# fregate

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)

> LLM benchmark suite — score models on code, reasoning, language, tools & features.

Benchmark any LLM (local or cloud) on real tasks. Compare models side-by-side with automated scoring and comparative scorecards.

*Formerly `ollama-model-benchmark` — merged into fregate v2.0 with multi-provider support.*

## Supported Providers

| Provider | Type | Models |
|----------|------|--------|
| **Ollama** | Local | Auto-discovered from `/api/tags` |
| **OpenAI** | Cloud | gpt-4o, gpt-4o-mini, o1, ... |
| **Anthropic** | Cloud | claude-sonnet-4, claude-haiku-4, ... |
| **OpenRouter** | Aggregator | 100+ models (Llama, Gemini, Mistral, ...) |
| **Groq** | Cloud | llama-3.3-70b, mixtral, ... |
| **Any OpenAI-compatible** | Custom | vLLM, LiteLLM, text-generation-webui, ... |

## Quick Start

```bash
git clone https://github.com/m4rv4x/ollama-model-benchmark.git
cd ollama-model-benchmark

python3 -m venv venv && source venv/bin/activate
pip install -e .

# Create config
fregate init

# Edit config.yaml with your providers
# Then run:
fregate models          # List available models
fregate tasks           # List benchmark tasks
fregate run             # Run benchmarks
```

## Benchmark Categories

| Category | Emoji | Tests | What it covers |
|----------|-------|-------|----------------|
| **code** | 💻 | 6 | Python, Bash, SQL, Rust — generation, debugging, security |
| **french** | 🇫🇷 | 4 | Grammaire, synthèse, traduction technique, ponctuation |
| **reasoning** | 🧠 | 5 | Logique, probabilités, diagnostic réseau, énigmes |
| **tools** | 🔧 | 4 | Function calling, multi-tool, choix d'outil, non-appel |
| **features** | ⚡ | 5 | JSON structuré, system prompt, contexte long, vitesse, refus |

## Usage

```bash
# Run all tasks on all models
fregate run

# Run on specific models
fregate run -m ollama-local:qwen3:32b -m openai:gpt-4o

# Filter by category
fregate run -C code -C reasoning

# Dry run (see what would execute)
fregate run --dry-run

# Show a saved report
fregate show reports/fregate_abc123_20260617.md
```

### Backward-compatible alias

The old `ollama-bench` command still works:
```bash
ollama-bench run qwen3:32b          # same as fregate run
ollama-bench compare a b            # same as fregate run -m a -m b
```

## Config

```yaml
providers:
  - name: ollama-local
    type: ollama
    base_url: http://localhost:11434

  - name: openai
    type: openai
    api_key: ${OPENAI_API_KEY}
    models:
      - gpt-4o
      - gpt-4o-mini

  - name: anthropic
    type: anthropic
    api_key: ${ANTHROPIC_API_KEY}
    models:
      - claude-sonnet-4-20250514

scoring:
  llm_grading: true
  grader_provider: ollama-local

output:
  dir: ./reports
  format: both  # markdown | json | both
```

API keys support `${ENV_VAR}` references.

## Scoring Methods

| Method | How it works | When to use |
|--------|-------------|-------------|
| `llm` | An LLM grades the response (0.0–1.0) | Open-ended questions |
| `exact` | Exact string match | Deterministic answers |
| `contains` | Checks for required keywords | Factual checks |
| `regex` | Pattern matching | Format validation |

Tool-use tasks are scored by checking if the right function was called.

## Adding Custom Tasks

Create a YAML file in your `tasks/` directory:

```yaml
category: code
tasks:
  - id: my_test
    name: "My custom test"
    prompt: "Write a Python function that..."
    expected_contains:
      - "def my_function"
    scoring: contains
    max_tokens: 1024
```

## License

[MIT](LICENSE) © [marvax](https://github.com/m4rv4x)
