#!/usr/bin/env python3
"""CLI pour ollama-model-benchmark."""
import argparse
import sys
from .runner import BenchmarkRunner
from .reporter import print_report, print_comparison


def main():
    p = argparse.ArgumentParser(prog="ollama-bench", description="Benchmark modeles Ollama")
    sub = p.add_subparsers(dest="cmd")

    r = sub.add_parser("run", help="Benchmark un modele")
    r.add_argument("model", help="Nom du modele")
    r.add_argument("--task", choices=["code", "french", "reasoning", "tool_use", "speed", "all"],
                   default="all")
    r.add_argument("--ollama", default="http://localhost:11434")

    c = sub.add_parser("compare", help="Comparer modeles")
    c.add_argument("models", nargs="+", help="Modeles a comparer")
    c.add_argument("--ollama", default="http://localhost:11434")

    sub.add_parser("report", help="Dernier rapport")

    sub.add_parser("list-models", help="Modeles disponibles")

    args = p.parse_args()
    if not args.cmd:
        p.print_help()
        sys.exit(1)

    runner = BenchmarkRunner(args.ollama if hasattr(args, "ollama") else None)

    if args.cmd == "run":
        results = runner.run(args.model, args.task)
        print_report(results)
    elif args.cmd == "compare":
        results = runner.compare(args.models)
        print_comparison(results)
    elif args.cmd == "report":
        runner.show_last_report()
    elif args.cmd == "list-models":
        runner.list_models()
