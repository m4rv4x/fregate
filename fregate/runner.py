"""Benchmark runner — orchestrates test execution across models."""
from __future__ import annotations

import time
import uuid
from pathlib import Path

from .models import (
    BenchmarkRun,
    ModelScorecard,
    TaskCategory,
    TaskResult,
    TestCase,
)
from .provider import Provider
from .scorer import score_response, score_tool_calls


class BenchmarkRunner:
    """Runs benchmark tasks against models and collects results."""

    def __init__(
        self,
        providers: list[Provider],
        tasks: list[TestCase],
        grader_provider: Provider | None = None,
        grader_model: str | None = None,
    ):
        self.providers = providers
        self.tasks = tasks
        self.grader_provider = grader_provider
        self.grader_model = grader_model

    def run(
        self,
        models: dict[str, list[str]] | None = None,
        categories: list[str] | None = None,
        callback=None,
    ) -> BenchmarkRun:
        """
        Run the full benchmark.

        Args:
            models: {provider_name: [model_name, ...]} — None = all
            categories: filter by category — None = all
            callback: fn(provider, model, test, result) called after each test
        """
        run = BenchmarkRun(run_id=str(uuid.uuid4())[:8])

        # Filter tasks by category
        tasks = self.tasks
        if categories:
            tasks = [t for t in tasks if t.category.value in categories]

        run.tasks_used = [t.id for t in tasks]

        for provider in self.providers:
            # Get models for this provider
            if models and provider.name in models:
                model_list = models[provider.name]
            else:
                model_list = provider.list_models()

            if not model_list:
                continue

            for model in model_list:
                scorecard = ModelScorecard(model=model, provider=provider.name)

                for task in tasks:
                    result = self._run_single(provider, model, task)
                    scorecard.results.append(result)

                    if callback:
                        callback(provider.name, model, task, result)

                run.scorecards.append(scorecard)

        return run

    def _run_single(self, provider: Provider, model: str, task: TestCase) -> TaskResult:
        """Run a single test case against a single model."""
        messages = []
        if task.system_prompt:
            messages.append({"role": "system", "content": task.system_prompt})
        messages.append({"role": "user", "content": task.prompt})

        # Execute
        result = provider.complete(
            model=model,
            messages=messages,
            max_tokens=task.max_tokens,
            temperature=task.temperature,
            tools=task.tools,
        )

        if result["error"]:
            return TaskResult(
                test_id=task.id,
                model=model,
                provider=provider.name,
                response="",
                score=0.0,
                latency_ms=result["latency_ms"],
                tokens_in=0,
                tokens_out=0,
                tokens_per_sec=0.0,
                error=result["error"],
            )

        # Score
        if task.tools and result["tool_calls"]:
            score, notes = score_tool_calls(task, result["tool_calls"])
        else:
            score, notes = score_response(
                task,
                result["content"],
                self.grader_provider,
                self.grader_model,
            )

        tps = (result["tokens_out"] / (result["latency_ms"] / 1000)) if result["latency_ms"] > 0 else 0

        return TaskResult(
            test_id=task.id,
            model=model,
            provider=provider.name,
            response=result["content"][:500],  # truncate stored response
            score=score,
            latency_ms=result["latency_ms"],
            tokens_in=result["tokens_in"],
            tokens_out=result["tokens_out"],
            tokens_per_sec=round(tps, 1),
            notes=notes,
        )
