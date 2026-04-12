"""Unit tests for the model-aware cost calculator."""

from __future__ import annotations

import pytest

from deployer.llm.cost_calculator import CostBreakdown, calculate_cost


class TestCalculateCost:
    def test_known_model_returns_nonzero_cost(self) -> None:
        result = calculate_cost("gpt-4o-mini", prompt_tokens=100, completion_tokens=50)
        assert isinstance(result, CostBreakdown)
        assert result.total_cost_usd > 0

    def test_zero_tokens_yields_zero_cost(self) -> None:
        result = calculate_cost("gpt-4o-mini", prompt_tokens=0, completion_tokens=0)
        assert result.total_cost_usd == 0.0
        assert result.prompt_cost_usd == 0.0
        assert result.completion_cost_usd == 0.0

    def test_prompt_and_completion_split(self) -> None:
        # For gpt-4o-mini: input=$0.15/1M, output=$0.60/1M
        result = calculate_cost("gpt-4o-mini", prompt_tokens=1_000_000, completion_tokens=0)
        assert abs(result.prompt_cost_usd - 0.15) < 1e-6

        result2 = calculate_cost("gpt-4o-mini", prompt_tokens=0, completion_tokens=1_000_000)
        assert abs(result2.completion_cost_usd - 0.60) < 1e-6

    def test_total_equals_sum_of_parts(self) -> None:
        result = calculate_cost("gpt-4o", prompt_tokens=500, completion_tokens=200)
        parts = result.prompt_cost_usd + result.completion_cost_usd
        assert abs(result.total_cost_usd - parts) < 1e-9

    def test_unknown_model_returns_zero_cost(self) -> None:
        result = calculate_cost("unknown-model-xyz", prompt_tokens=100, completion_tokens=100)
        assert result.total_cost_usd == 0.0

    def test_versioned_model_prefix_match(self) -> None:
        # "gpt-4o-2024-05-13" should match "gpt-4o" pricing
        versioned = calculate_cost("gpt-4o-2024-05-13", prompt_tokens=1000, completion_tokens=1000)
        canonical = calculate_cost("gpt-4o", prompt_tokens=1000, completion_tokens=1000)
        assert versioned.total_cost_usd == canonical.total_cost_usd

    def test_more_expensive_model_costs_more(self) -> None:
        cheap = calculate_cost("gpt-4o-mini", prompt_tokens=1000, completion_tokens=1000)
        expensive = calculate_cost("gpt-4o", prompt_tokens=1000, completion_tokens=1000)
        assert expensive.total_cost_usd > cheap.total_cost_usd

    def test_anthropic_model_pricing(self) -> None:
        result = calculate_cost("claude-sonnet-4-6", prompt_tokens=1_000_000, completion_tokens=0)
        assert abs(result.prompt_cost_usd - 3.00) < 1e-6

    @pytest.mark.parametrize(
        "model",
        [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
            "claude-opus-4-6",
            "claude-sonnet-4-6",
        ],
    )
    def test_all_known_models_return_cost(self, model: str) -> None:
        result = calculate_cost(model, prompt_tokens=100, completion_tokens=100)
        assert result.total_cost_usd > 0
