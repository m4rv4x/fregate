# ollama-model-benchmark

Benchmark tes modeles Ollama locaux sur des taches precises. Scorecard, comparaison, export.

## Features

- Taches : code, francais, reasoning, tool_use, vitesse
- Scorecard markdown par modele
- Tableau comparatif
- Support endpoints Ollama multiples (local + remote)
- Mesure temps de reponse et tokens/sec

## Installation

```bash
cd ~/Projects/ollama-model-benchmark
python3 -m venv venv && source venv/bin/activate
pip install -e .
```

## Usage

```bash
ollama-bench run qwen3:32b                    # Benchmark complet
ollama-bench run qwen3:32b --task code        # Tache specifique
ollama-bench compare qwen3:32b mimo-v2.5-pro  # Comparer
ollama-bench report                            # Dernier rapport
ollama-bench list-models                       # Modeles disponibles
```

## Structure

```
ollama-model-benchmark/
├── ollama_benchmark/
│   ├── __init__.py
│   ├── cli.py          # CLI principal
│   ├── runner.py       # Orchestration benchmarks
│   ├── tasks.py        # Definitions taches
│   ├── reporter.py     # Generation scorecard
│   ├── compare.py      # Comparaison modeles
│   └── client.py       # Client Ollama
├── tests/
├── pyproject.toml
└── README.md
```
