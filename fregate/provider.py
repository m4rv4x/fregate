"""Unified provider abstraction — wraps litellm for all providers."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import litellm

# Suppress litellm noise
litellm.suppress_debug_info = True


@dataclass
class ProviderConfig:
    name: str
    type: str          # ollama | openai | anthropic | openrouter | groq | openai_compatible
    base_url: str | None = None
    api_key: str | None = None
    models: list[str] | None = None


def _resolve_env(val: str | None) -> str | None:
    """Resolve ${ENV_VAR} references in config values."""
    if val and val.startswith("${") and val.endswith("}"):
        return os.environ.get(val[2:-1], "")
    return val


def _to_litellm_model(model: str, provider_type: str, base_url: str | None) -> str:
    """Convert a model name to litellm's expected format."""
    if provider_type == "ollama":
        return f"ollama/{model}"
    elif provider_type == "openai":
        return model  # litellm handles openai natively
    elif provider_type == "anthropic":
        return f"anthropic/{model}"
    elif provider_type == "openrouter":
        return f"openrouter/{model}"
    elif provider_type == "groq":
        return f"groq/{model}"
    elif provider_type == "openai_compatible":
        return f"openai/{model}"  # will use base_url
    return model


def _build_kwargs(
    provider: ProviderConfig,
    model: str,
    messages: list[dict],
    max_tokens: int = 2048,
    temperature: float = 0.2,
    tools: list[dict] | None = None,
) -> dict[str, Any]:
    """Build litellm completion kwargs."""
    litellm_model = _to_litellm_model(model, provider.type, provider.base_url)

    kwargs: dict[str, Any] = {
        "model": litellm_model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    api_key = _resolve_env(provider.api_key)
    if api_key:
        kwargs["api_key"] = api_key

    if provider.base_url:
        kwargs["api_base"] = provider.base_url

    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    return kwargs


class Provider:
    """Unified provider that talks to any LLM via litellm."""

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.name = config.name
        self.type = config.type

    def list_models(self) -> list[str]:
        """Return available models for this provider."""
        if self.config.models:
            return list(self.config.models)

        # Auto-discover for Ollama
        if self.config.type == "ollama":
            try:
                import requests
                base = self.config.base_url or "http://localhost:11434"
                resp = requests.get(f"{base}/api/tags", timeout=5)
                data = resp.json()
                return [m["name"] for m in data.get("models", [])]
            except Exception:
                return []

        return []

    def complete(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int = 2048,
        temperature: float = 0.2,
        tools: list[dict] | None = None,
    ) -> dict[str, Any]:
        """
        Send a completion request. Returns:
        {
            "content": str,
            "tokens_in": int,
            "tokens_out": int,
            "latency_ms": float,
            "tool_calls": list | None,
            "error": str | None,
        }
        """
        kwargs = _build_kwargs(self.config, model, messages, max_tokens, temperature, tools)

        t0 = time.perf_counter()
        try:
            response = litellm.completion(**kwargs)
            latency = (time.perf_counter() - t0) * 1000

            usage = getattr(response, "usage", None)
            tokens_in = getattr(usage, "prompt_tokens", 0) or 0
            tokens_out = getattr(usage, "completion_tokens", 0) or 0

            choice = response.choices[0]
            content = choice.message.content or ""

            # Extract tool calls if present
            tool_calls = None
            if hasattr(choice.message, "tool_calls") and choice.message.tool_calls:
                tool_calls = []
                for tc in choice.message.tool_calls:
                    tool_calls.append({
                        "id": tc.id,
                        "function": tc.function.name,
                        "arguments": tc.function.arguments,
                    })

            return {
                "content": content,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "latency_ms": latency,
                "tool_calls": tool_calls,
                "error": None,
            }

        except Exception as e:
            latency = (time.perf_counter() - t0) * 1000
            return {
                "content": "",
                "tokens_in": 0,
                "tokens_out": 0,
                "latency_ms": latency,
                "tool_calls": None,
                "error": str(e),
            }


def discover_ollama_models(base_url: str = "http://localhost:11434") -> list[str]:
    """Quick Ollama model discovery."""
    try:
        import requests
        resp = requests.get(f"{base_url}/api/tags", timeout=5)
        data = resp.json()
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []
