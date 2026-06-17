"""Data models for Fregate."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskCategory(str, Enum):
    CODE = "code"
    FRENCH = "french"
    REASONING = "reasoning"
    TOOLS = "tools"
    FEATURES = "features"


@dataclass
class TestCase:
    """A single benchmark test case."""
    id: str
    category: TaskCategory
    name: str
    prompt: str
    system_prompt: str | None = None
    expected: str | None = None          # for exact/regex scoring
    expected_contains: list[str] = field(default_factory=list)
    expected_not_contains: list[str] = field(default_factory=list)
    scoring: str = "llm"                 # llm | exact | contains | regex
    max_tokens: int = 2048
    temperature: float = 0.2
    tools: list[dict[str, Any]] | None = None   # for tool-use tests
    tags: list[str] = field(default_factory=list)
    weight: float = 1.0


@dataclass
class TaskResult:
    """Result of running one test case against one model."""
    test_id: str
    model: str
    provider: str
    response: str
    score: float                          # 0.0 – 1.0
    latency_ms: float
    tokens_in: int
    tokens_out: int
    tokens_per_sec: float
    error: str | None = None
    notes: str = ""                       # grader explanation


@dataclass
class ModelScorecard:
    """Aggregated scores for a model across all tasks."""
    model: str
    provider: str
    results: list[TaskResult] = field(default_factory=list)

    @property
    def avg_score(self) -> float:
        if not self.results:
            return 0.0
        total_weight = sum(
            float(r.test_id.split("_")[0] != "" and 1.0 or 1.0) for r in self.results
        )
        return sum(r.score for r in self.results) / len(self.results)

    @property
    def avg_latency_ms(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.latency_ms for r in self.results) / len(self.results)

    @property
    def avg_tokens_per_sec(self) -> float:
        if not self.results:
            return 0.0
        valid = [r for r in self.results if r.tokens_per_sec > 0]
        if not valid:
            return 0.0
        return sum(r.tokens_per_sec for r in valid) / len(valid)

    def score_by_category(self) -> dict[str, float]:
        cats: dict[str, list[float]] = {}
        for r in self.results:
            cat = r.test_id.split("/")[0] if "/" in r.test_id else "other"
            cats.setdefault(cat, []).append(r.score)
        return {cat: sum(s) / len(s) for cat, s in cats.items()}

    @property
    def error_count(self) -> int:
        return sum(1 for r in self.results if r.error)


@dataclass
class BenchmarkRun:
    """A full benchmark run across models and tasks."""
    run_id: str
    timestamp: float = field(default_factory=time.time)
    config_hash: str = ""
    scorecards: list[ModelScorecard] = field(default_factory=list)
    tasks_used: list[str] = field(default_factory=list)
