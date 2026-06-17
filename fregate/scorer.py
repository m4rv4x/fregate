"""Scoring engine — grades model responses."""
from __future__ import annotations

import json
import re

from .models import TestCase
from .provider import Provider


GRADING_SYSTEM = """You are an impartial LLM benchmark grader. You evaluate a model's response
against the expected answer for a given task.

Score from 0.0 to 1.0:
- 1.0 = perfect, complete, correct
- 0.8 = mostly correct, minor issues
- 0.6 = partially correct, missing key elements
- 0.4 = significant errors or omissions
- 0.2 = mostly wrong
- 0.0 = completely wrong, irrelevant, or refused

Respond ONLY with valid JSON:
{"score": 0.0-1.0, "notes": "brief explanation"}
"""

GRADING_PROMPT = """## Task
{task_name}

## Prompt given to the model
{prompt}

## Expected answer
{expected}

## Model's response
{response}

Grade this response. Output ONLY valid JSON."""


def score_response(
    test: TestCase,
    response: str,
    grader_provider: Provider | None = None,
    grader_model: str | None = None,
) -> tuple[float, str]:
    """
    Score a response. Returns (score, notes).
    Uses deterministic scoring when possible, LLM grading otherwise.
    """
    if test.scoring == "exact" and test.expected:
        clean_resp = response.strip().lower()
        clean_exp = test.expected.strip().lower()
        if clean_resp == clean_exp:
            return 1.0, "Exact match"
        # partial match
        if clean_exp in clean_resp:
            return 0.7, "Expected found within response"
        return 0.0, f"Expected '{test.expected}', got '{response[:100]}'"

    if test.scoring == "contains":
        score = 1.0
        notes_parts = []
        for keyword in test.expected_contains:
            if keyword.lower() not in response.lower():
                score -= 1.0 / max(len(test.expected_contains), 1)
                notes_parts.append(f"missing: {keyword}")
        for keyword in test.expected_not_contains:
            if keyword.lower() in response.lower():
                score -= 0.2
                notes_parts.append(f"should not contain: {keyword}")
        score = max(0.0, min(1.0, score))
        notes = "; ".join(notes_parts) if notes_parts else "All checks passed"
        return score, notes

    if test.scoring == "regex" and test.expected:
        try:
            if re.search(test.expected, response, re.IGNORECASE | re.DOTALL):
                return 1.0, "Regex match"
            return 0.0, "No regex match"
        except re.error:
            return 0.0, f"Invalid regex: {test.expected}"

    # LLM grading (default)
    if grader_provider and test.expected:
        return _llm_grade(test, response, grader_provider, grader_model)

    # No grader and no expected — score based on non-empty response
    if response.strip():
        return 0.5, "Non-empty response (no grader available)"
    return 0.0, "Empty response"


def _llm_grade(
    test: TestCase,
    response: str,
    grader: Provider,
    grader_model: str | None,
) -> tuple[float, str]:
    """Use an LLM to grade the response."""
    model = grader_model or (grader.config.models[0] if grader.config.models else "")
    if not model:
        return 0.5, "No grader model available"

    prompt = GRADING_PROMPT.format(
        task_name=test.name,
        prompt=test.prompt,
        expected=test.expected or "(open-ended evaluation)",
        response=response[:3000],  # truncate for grader context
    )

    messages = [
        {"role": "system", "content": GRADING_SYSTEM},
        {"role": "user", "content": prompt},
    ]

    result = grader.complete(model, messages, max_tokens=256, temperature=0.1)

    if result["error"]:
        return 0.5, f"Grader error: {result['error']}"

    try:
        # Extract JSON from response (handle markdown code blocks)
        raw = result["content"].strip()
        if "```" in raw:
            raw = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
            raw = raw.group(1).strip() if raw else result["content"]
        parsed = json.loads(raw)
        score = float(parsed.get("score", 0.5))
        notes = str(parsed.get("notes", ""))
        return max(0.0, min(1.0, score)), notes
    except (json.JSONDecodeError, ValueError, TypeError):
        return 0.5, f"Grader output not parseable: {result['content'][:200]}"


def score_tool_calls(
    test: TestCase,
    tool_calls: list[dict] | None,
) -> tuple[float, str]:
    """Score tool-use responses by checking if the right function was called."""
    if not test.tools:
        return 0.0, "No tools defined in test"

    if not tool_calls:
        return 0.0, "No tool calls made"

    # Check if any tool call matches expected function names
    expected_funcs = set()
    for tool in test.tools:
        if "function" in tool and "name" in tool["function"]:
            expected_funcs.add(tool["function"]["name"])

    called_funcs = {tc["function"] for tc in tool_calls}

    if called_funcs & expected_funcs:
        overlap = len(called_funcs & expected_funcs) / len(expected_funcs)
        return min(1.0, overlap), f"Called: {called_funcs}"

    return 0.1, f"Expected {expected_funcs}, called {called_funcs}"
