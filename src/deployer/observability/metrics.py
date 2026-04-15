"""Prometheus metrics for the LLM proxy.

LLM-specific counters, histograms, and gauges. Standard HTTP request metrics
are already covered by the middleware + logger — these focus on what is
uniquely useful for LLM operations (tokens, cost, TTFT, cache, circuit
breaker, provider errors).
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# Latency buckets tuned for LLM calls (1s–60s is the useful range).
_DURATION_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)
# Cost buckets in USD — most requests are sub-cent, tail can reach $1+.
_COST_BUCKETS = (0.0001, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0)

llm_tokens_total = Counter(
    "llm_tokens_total",
    "Total tokens processed",
    labelnames=("model", "direction", "api_key"),
)

llm_request_cost_usd = Histogram(
    "llm_request_cost_usd",
    "Cost distribution per request in USD",
    labelnames=("model", "api_key"),
    buckets=_COST_BUCKETS,
)

llm_cost_total_usd = Counter(
    "llm_cost_total_usd",
    "Cumulative cost in USD",
    labelnames=("model", "api_key"),
)

llm_request_duration_seconds = Histogram(
    "llm_request_duration_seconds",
    "End-to-end LLM request duration",
    labelnames=("model", "stream"),
    buckets=_DURATION_BUCKETS,
)

llm_time_to_first_token_seconds = Histogram(
    "llm_time_to_first_token_seconds",
    "Streaming time-to-first-token",
    labelnames=("model",),
    buckets=_DURATION_BUCKETS,
)

llm_cache_hits_total = Counter(
    "llm_cache_hits_total",
    "Response cache hits",
    labelnames=("model",),
)

llm_cache_misses_total = Counter(
    "llm_cache_misses_total",
    "Response cache misses",
    labelnames=("model",),
)

# 0=closed, 1=open, 2=half-open
llm_circuit_breaker_state = Gauge(
    "llm_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half-open)",
    labelnames=("provider",),
)

llm_rate_limit_rejected_total = Counter(
    "llm_rate_limit_rejected_total",
    "Requests rejected by rate limiting",
    labelnames=("api_key",),
)

llm_provider_errors_total = Counter(
    "llm_provider_errors_total",
    "Provider-side errors",
    labelnames=("provider", "error_type"),
)
