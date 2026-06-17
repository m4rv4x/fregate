"""Built-in benchmark task definitions."""
from __future__ import annotations

from pathlib import Path

import yaml

from .models import TaskCategory, TestCase


def load_tasks(tasks_dir: str | Path) -> list[TestCase]:
    """Load all .yaml task files from a directory."""
    tasks_dir = Path(tasks_dir)
    all_tasks: list[TestCase] = []

    if not tasks_dir.exists():
        return all_tasks

    for yaml_file in sorted(tasks_dir.glob("*.yaml")):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        if not data or "tasks" not in data:
            continue

        category_str = data.get("category", yaml_file.stem)
        try:
            category = TaskCategory(category_str)
        except ValueError:
            category = TaskCategory.FEATURES

        for t in data["tasks"]:
            tc = TestCase(
                id=f"{category.value}/{t['id']}",
                category=category,
                name=t["name"],
                prompt=t["prompt"],
                system_prompt=t.get("system_prompt"),
                expected=t.get("expected"),
                expected_contains=t.get("expected_contains", []),
                expected_not_contains=t.get("expected_not_contains", []),
                scoring=t.get("scoring", "llm"),
                max_tokens=t.get("max_tokens", 2048),
                temperature=t.get("temperature", 0.2),
                tools=t.get("tools"),
                tags=t.get("tags", []),
                weight=t.get("weight", 1.0),
            )
            all_tasks.append(tc)

    return all_tasks


def list_task_categories(tasks_dir: str | Path) -> dict[str, int]:
    """Return category -> count mapping."""
    tasks = load_tasks(tasks_dir)
    cats: dict[str, int] = {}
    for t in tasks:
        cats[t.category.value] = cats.get(t.category.value, 0) + 1
    return cats
