"""CLI for Fregate — LLM benchmark suite."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from . import __version__
from .models import TaskCategory
from .provider import Provider, ProviderConfig, _resolve_env, discover_ollama_models
from .runner import BenchmarkRunner
from .tasks import load_tasks, list_task_categories
from .report import save_report, generate_markdown

console = Console()

DEFAULT_CONFIG = "config.yaml"


def _load_config(path: str) -> dict:
    """Load and validate config file."""
    p = Path(path)
    if not p.exists():
        console.print(f"[red]Config not found:[/] {path}")
        console.print(f"Run [cyan]fregate init[/] to create one.")
        sys.exit(1)
    with open(p) as f:
        return yaml.safe_load(f)


def _build_providers(config: dict) -> list[Provider]:
    """Build provider instances from config."""
    providers = []
    for pc in config.get("providers", []):
        pcfg = ProviderConfig(
            name=pc["name"],
            type=pc["type"],
            base_url=pc.get("base_url"),
            api_key=pc.get("api_key"),
            models=pc.get("models"),
        )
        providers.append(Provider(pcfg))
    return providers


def _build_grader(config: dict, providers: list[Provider]) -> tuple[Provider | None, str | None]:
    """Build grader provider from config."""
    scoring = config.get("scoring", {})
    if not scoring.get("llm_grading", True):
        return None, None

    grader_name = scoring.get("grader_provider")
    grader_model = scoring.get("grader_model")

    if grader_name:
        for p in providers:
            if p.name == grader_name:
                models = p.list_models()
                return p, grader_model or (models[0] if models else None)

    # Default: use first provider
    if providers:
        models = providers[0].list_models()
        return providers[0], grader_model or (models[0] if models else None)

    return None, None


@click.group()
@click.version_option(__version__, prog_name="fregate")
def main():
    """Fregate — LLM benchmark suite.

    Benchmark local and cloud models on code, reasoning, language, tools & features.
    """
    pass


@main.command()
@click.option("--path", default=DEFAULT_CONFIG, help="Config file path")
def init(path):
    """Create a starter config file."""
    if Path(path).exists():
        console.print(f"[yellow]Config already exists:[/] {path}")
        if not click.confirm("Overwrite?"):
            return

    # Copy example config
    example = Path(__file__).parent.parent / "config.example.yaml"
    if example.exists():
        import shutil
        shutil.copy(example, path)
    else:
        # Generate minimal config
        config = {
            "providers": [
                {
                    "name": "ollama-local",
                    "type": "ollama",
                    "base_url": "http://localhost:11434",
                }
            ],
            "tasks_dir": "./tasks",
            "scoring": {"llm_grading": True},
            "output": {"dir": "./reports", "format": "both"},
        }
        with open(path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    console.print(f"[green]✓ Config created:[/] {path}")
    console.print("Edit it to add your providers and API keys.")


@main.command()
@click.option("-c", "--config", default=DEFAULT_CONFIG, help="Config file")
def models(config):
    """List available models across all providers."""
    cfg = _load_config(config)
    providers = _build_providers(cfg)

    table = Table(title="Available Models", show_lines=True)
    table.add_column("Provider", style="cyan")
    table.add_column("Type", style="dim")
    table.add_column("Model", style="green")

    for provider in providers:
        model_list = provider.list_models()
        if not model_list:
            table.add_row(provider.name, provider.type, "[dim]No models found[/]")
        else:
            for i, m in enumerate(model_list):
                prov = provider.name if i == 0 else ""
                typ = provider.type if i == 0 else ""
                table.add_row(prov, typ, m)

    console.print(table)


@main.command()
@click.option("-c", "--config", default=DEFAULT_CONFIG, help="Config file")
def tasks(config):
    """List available benchmark tasks."""
    cfg = _load_config(config)
    tasks_dir = cfg.get("tasks_dir", "./tasks")

    cats = list_task_categories(tasks_dir)
    if not cats:
        console.print("[yellow]No tasks found.[/] Add YAML files to your tasks/ directory.")
        return

    table = Table(title="Benchmark Tasks")
    table.add_column("Category", style="cyan")
    table.add_column("Count", style="green", justify="right")

    total = 0
    for cat, count in sorted(cats.items()):
        emoji = {"code": "💻", "french": "🇫🇷", "reasoning": "🧠", "tools": "🔧", "features": "⚡"}.get(cat, "📋")
        table.add_row(f"{emoji} {cat}", str(count))
        total += count

    table.add_row("[bold]Total[/]", f"[bold]{total}[/]")
    console.print(table)


@main.command()
@click.option("-c", "--config", default=DEFAULT_CONFIG, help="Config file")
@click.option("-m", "--model", multiple=True, help="Specific model(s) to benchmark (provider:model)")
@click.option("-C", "--category", multiple=True, help="Filter by category (code, french, reasoning, tools, features)")
@click.option("--dry-run", is_flag=True, help="Show what would run without executing")
def run(config, model, category, dry_run):
    """Run benchmarks on configured models."""
    cfg = _load_config(config)
    providers = _build_providers(cfg)

    if not providers:
        console.print("[red]No providers configured.[/] Edit your config.yaml.")
        sys.exit(1)

    # Load tasks
    tasks_dir = cfg.get("tasks_dir", "./tasks")
    # Resolve relative to config file location
    config_dir = Path(config).parent
    abs_tasks_dir = config_dir / tasks_dir
    all_tasks = load_tasks(abs_tasks_dir)

    if not all_tasks:
        console.print(f"[red]No tasks found in[/] {abs_tasks_dir}")
        sys.exit(1)

    # Filter tasks
    cats = list(category) if category else None
    if cats:
        all_tasks = [t for t in all_tasks if t.category.value in cats]
        if not all_tasks:
            console.print(f"[red]No tasks match categories:[/] {cats}")
            sys.exit(1)

    # Parse model selection
    models_dict: dict[str, list[str]] | None = None
    if model:
        models_dict = {}
        for m in model:
            if ":" in m:
                prov_name, mod_name = m.split(":", 1)
                models_dict.setdefault(prov_name, []).append(mod_name)
            else:
                # Try all providers
                for p in providers:
                    models_dict.setdefault(p.name, []).append(m)

    # Build grader
    grader_provider, grader_model = _build_grader(cfg, providers)

    # Preview
    console.print(Panel(
        f"[bold]Fregate v{__version__}[/] · {len(all_tasks)} tasks · "
        f"{len(providers)} providers",
        title="🏁 Benchmark",
        border_style="cyan",
    ))

    if dry_run:
        console.print("\n[bold]Dry run — tasks:[/]")
        for t in all_tasks:
            console.print(f"  • {t.id}: {t.name}")
        console.print("\n[bold]Models:[/]")
        for p in providers:
            mlist = models_dict.get(p.name, p.list_models()) if models_dict else p.list_models()
            for m in mlist:
                console.print(f"  • {p.name}:{m}")
        return

    # Run with progress
    runner = BenchmarkRunner(providers, all_tasks, grader_provider, grader_model)

    total_tests = 0
    for p in providers:
        mlist = models_dict.get(p.name, p.list_models()) if models_dict else p.list_models()
        total_tests += len(mlist) * len(all_tasks)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Benchmarking...", total=total_tests)

        def on_result(provider_name, model_name, test, result):
            progress.advance(task)
            status = "✓" if result.score >= 0.6 else "✗"
            color = "green" if result.score >= 0.6 else "red"
            progress.update(task, description=f"[{color}]{status}[/] {model_name}/{test.id}")

        benchmark = runner.run(models=models_dict, categories=cats, callback=on_result)

    # Generate and save report
    output_cfg = cfg.get("output", {})
    output_dir = output_cfg.get("dir", "./reports")
    output_fmt = output_cfg.get("format", "both")

    abs_output_dir = config_dir / output_dir
    saved = save_report(benchmark, str(abs_output_dir), output_fmt)

    # Print summary
    console.print()
    sorted_cards = sorted(benchmark.scorecards, key=lambda c: c.avg_score, reverse=True)

    table = Table(title="📊 Results")
    table.add_column("Rank", style="dim", width=4)
    table.add_column("Model", style="bold")
    table.add_column("Score", justify="right")
    table.add_column("Latency", justify="right")
    table.add_column("Tok/s", justify="right")

    for i, card in enumerate(sorted_cards, 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
        score_pct = f"{card.avg_score:.0%}"
        color = "green" if card.avg_score >= 0.8 else "yellow" if card.avg_score >= 0.6 else "red"
        table.add_row(
            medal,
            f"{card.provider}:{card.model}",
            f"[{color}]{score_pct}[/]",
            f"{card.avg_latency_ms:.0f}ms",
            f"{card.avg_tokens_per_sec:.0f}",
        )

    console.print(table)
    console.print(f"\n[green]Reports saved:[/]")
    for s in saved:
        console.print(f"  📄 {s}")


@main.command()
@click.argument("report_path")
def show(report_path):
    """Display a saved markdown report."""
    p = Path(report_path)
    if not p.exists():
        console.print(f"[red]Report not found:[/] {report_path}")
        sys.exit(1)
    console.print(p.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
