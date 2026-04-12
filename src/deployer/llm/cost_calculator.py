"""Model-aware cost calculator for LLM requests."""

from __future__ import annotations

from dataclasses import dataclass

# Pricing per 1M tokens (USD) — input / output.
# Sources: OpenAI and Anthropic pricing pages (April 2026).
_MODEL_PRICING: dict[str, tuple[float, float]] = {
    # OpenAI
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-4": (30.00, 60.00),
    "gpt-3.5-turbo": (0.50, 1.50),
    "o1": (15.00, 60.00),
    "o1-mini": (3.00, 12.00),
    "o3-mini": (1.10, 4.40),
    # Anthropic
    "claude-opus-4-6": (15.00, 75.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5-20251001": (0.80, 4.00),
    "claude-3-5-sonnet-20241022": (3.00, 15.00),
    "claude-3-5-haiku-20241022": (1.00, 5.00),
    "claude-3-opus-20240229": (15.00, 75.00),
}

# USD per token = pricing per 1M / 1_000_000
_TOKENS_PER_DOLLAR_UNIT = 1_000_000


@dataclass(frozen=True)
class CostBreakdown:
    """Cost result for a single request."""

    prompt_cost_usd: float
    completion_cost_usd: float
    total_cost_usd: float


def _resolve_pricing(model: str) -> tuple[float, float]:
    """Return (input_price_per_1M, output_price_per_1M) for a model.

    Performs prefix matching so that versioned model names like
    'gpt-4o-2024-05-13' match the canonical 'gpt-4o' entry.
    Falls back to a zero-cost sentinel if the model is unknown.
    """
    if model in _MODEL_PRICING:
        return _MODEL_PRICING[model]
    # Prefix match: try longest matching key first
    for key in sorted(_MODEL_PRICING, key=len, reverse=True):
        if model.startswith(key):
            return _MODEL_PRICING[key]
    return (0.0, 0.0)  # unknown model — no cost recorded


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> CostBreakdown:
    """Calculate the USD cost for a completed LLM request."""
    input_price, output_price = _resolve_pricing(model)
    prompt_cost = (prompt_tokens / _TOKENS_PER_DOLLAR_UNIT) * input_price
    completion_cost = (completion_tokens / _TOKENS_PER_DOLLAR_UNIT) * output_price
    return CostBreakdown(
        prompt_cost_usd=round(prompt_cost, 8),
        completion_cost_usd=round(completion_cost, 8),
        total_cost_usd=round(prompt_cost + completion_cost, 8),
    )
