# `deployer` — Production-Ready Deploy Template for LLM Applications

## Briefing for Claude Code Agent

---

## 1. Improvements Applied

Changes from the original prompt and rationale:

| Original | Problem | Fix |
|----------|---------|-----|
| No secret management | `.env` files get committed, no rotation strategy | Add `.env.example` + `docker secrets` support + documentation on vault integration |
| No API key auth | Template is open to anyone — not production-ready | Add simple API key middleware (header-based), no full RBAC |
| Nginx as reverse proxy | Adds operational complexity for a template project | Drop Nginx. FastAPI + Uvicorn behind Docker is enough. Mention Nginx/Traefik as optional production layer in docs |
| "LLM template" but no LLM-specific concerns | Nothing differentiates this from a generic FastAPI template | Add: token counting middleware, per-request cost tracking, prompt/completion logging, streaming support, LLM provider abstraction, request/response guardrails hooks |
| Prometheus + Grafana without LLM metrics | Generic infra metrics miss the point | Add LLM-specific metrics: tokens_used, cost_per_request, latency_to_first_token, model distribution, cache hit rate |
| No caching layer | Every identical prompt hits the LLM API = wasted money | Add semantic response cache with TTL (Redis) |
| No graceful degradation | LLM provider goes down = app goes down | Add circuit breaker pattern, fallback responses, timeout config |
| Missing health check depth | `/health` returning 200 is not enough | Add deep health check: LLM provider reachability, Redis connectivity, system resource usage |
| pre-commit hooks listed but not specified | Vague | Define: ruff (lint + format), mypy, detect-secrets |

---

## 2. Problem Statement

Most AI projects die in notebooks. Teams that do get to production spend weeks solving the same problems: rate limiting, cost tracking, structured logging, health checks, secret management. This template provides a cloneable, opinionated starting point that handles production concerns so developers can focus on their LLM logic.

This is not a generic FastAPI boilerplate. Every component exists because LLM applications have specific operational needs that traditional web APIs do not: non-deterministic outputs, token-based billing, high latency variance, streaming responses, and cost that scales with usage rather than compute.

---

## 3. Architecture

```
Client Request
    |
    v
[FastAPI Application]
    |
    +-- API Key Auth Middleware
    +-- Rate Limiting Middleware (sliding window, per-key)
    +-- Request ID + Structured Logging Middleware
    |
    v
[Router Layer]
    |
    +-- /v1/chat/completions  (OpenAI-compatible)
    +-- /v1/completions       (simple prompt/response)
    +-- /health               (deep health check)
    +-- /health/ready          (readiness probe)
    +-- /metrics              (Prometheus scrape endpoint)
    |
    v
[LLM Service Layer]
    |
    +-- Provider Abstraction (OpenAI, Anthropic — swappable via config)
    +-- Token Counter (pre-request estimation + post-response actual)
    +-- Cost Calculator (model-aware pricing)
    +-- Response Cache (Redis, semantic dedup by prompt hash)
    +-- Circuit Breaker (fail-fast on provider outage)
    +-- Guardrails Hooks (pre/post processing — extensible)
    |
    v
[Observability Layer]
    |
    +-- Structured JSON Logging (structlog)
    +-- Prometheus Metrics (LLM-specific + standard HTTP)
    +-- Grafana Dashboard (pre-built JSON, importable)
    +-- Cost Tracking (per-key, per-model, per-day aggregation)

[Infrastructure]
    |
    +-- Docker + Docker Compose (app + Redis + Prometheus + Grafana)
    +-- GitHub Actions (lint, type check, test, build image)
    +-- Pydantic Settings (env-based, typed, validated)
```

---

## 4. What Makes This an LLM Template (Not a Generic FastAPI Boilerplate)

Every feature below exists because LLM workloads are fundamentally different from traditional APIs:

- **Token counting middleware** — LLM billing is per-token, not per-request. Every request logs input/output tokens and estimated cost.
- **Cost tracking** — Aggregates spending per API key, per model, per time window. Prevents bill shock.
- **Streaming support** — LLM responses can take 5-30s. Streaming (SSE) is not optional for production UX.
- **Response caching** — Identical prompts should not hit the LLM twice. SHA-256 hash of (model + messages + temperature) as cache key.
- **Circuit breaker** — LLM providers have outages. The app should degrade gracefully, not hang.
- **Guardrails hooks** — Pre-processing (PII detection, input validation) and post-processing (output filtering) are extensible injection points.
- **OpenAI-compatible API** — The `/v1/chat/completions` endpoint follows OpenAI's API spec. Any client that works with OpenAI works with this template.
- **Model-aware rate limiting** — Different models have different costs. Rate limits can vary per model tier.

---

## 5. Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Framework | FastAPI | Async-first, typed, OpenAPI docs built-in, industry standard for Python APIs |
| Server | Uvicorn | ASGI server, production-grade with `--workers` for multi-process |
| Config | pydantic-settings | Typed env vars, validation on startup, `.env` file support |
| Caching | Redis | In-memory, TTL support, also used for rate limiting sliding window |
| Logging | structlog | Structured JSON logs, context binding (request_id, api_key, model) |
| Metrics | prometheus-client | Standard metrics exposition, Grafana-compatible |
| Dashboards | Grafana | Pre-built dashboard JSON included, no manual setup |
| HTTP Client | httpx | Async HTTP for LLM provider calls, streaming support, timeouts |
| Testing | pytest + httpx + pytest-asyncio | Async test support, TestClient via httpx |
| Linting | ruff | Fast, replaces flake8 + isort + black in one tool |
| Type Checking | mypy | Static type analysis, strict mode |
| Secrets Detection | detect-secrets | Pre-commit hook to prevent secret leaks |
| CI/CD | GitHub Actions | Lint, type check, test, Docker build — on every push |
| Containerization | Docker + Docker Compose | Multi-service setup: app + Redis + Prometheus + Grafana |
| Rate Limiting | Custom middleware (Redis-backed) | Sliding window per API key, configurable per model |

---

## 6. Project Structure

```
deployer/
+-- src/
|   +-- deployer/
|       +-- __init__.py
|       +-- main.py                     # FastAPI app factory, lifespan events
|       +-- config.py                   # Pydantic Settings — all env vars, defaults, validation
|       +-- middleware/
|       |   +-- __init__.py
|       |   +-- auth.py                # API key validation (header: X-API-Key)
|       |   +-- rate_limit.py          # Sliding window rate limiter (Redis-backed)
|       |   +-- request_id.py          # Inject X-Request-ID, bind to logger context
|       |   +-- logging.py            # Request/response structured logging
|       +-- api/
|       |   +-- __init__.py
|       |   +-- router.py             # Main router aggregating all routes
|       |   +-- v1/
|       |       +-- __init__.py
|       |       +-- chat.py           # POST /v1/chat/completions (OpenAI-compatible)
|       |       +-- completions.py    # POST /v1/completions (simple mode)
|       |       +-- health.py         # GET /health, GET /health/ready
|       |       +-- schemas.py        # Request/Response Pydantic models
|       +-- llm/
|       |   +-- __init__.py
|       |   +-- providers/
|       |   |   +-- __init__.py
|       |   |   +-- base.py           # Abstract provider interface
|       |   |   +-- openai.py         # OpenAI API implementation
|       |   |   +-- anthropic.py      # Anthropic API implementation
|       |   +-- token_counter.py      # tiktoken-based token counting
|       |   +-- cost_calculator.py    # Model-aware cost per request
|       |   +-- cache.py             # Response cache (Redis, SHA-256 key)
|       |   +-- circuit_breaker.py   # Circuit breaker with configurable thresholds
|       |   +-- guardrails.py        # Pre/post processing hooks (extensible)
|       +-- observability/
|       |   +-- __init__.py
|       |   +-- metrics.py           # Prometheus metrics definitions
|       |   +-- logger.py            # structlog configuration
|       +-- dependencies.py          # FastAPI dependency injection (Redis, provider, etc.)
+-- tests/
|   +-- conftest.py                  # Fixtures: test client, mock provider, mock Redis
|   +-- unit/
|   |   +-- test_token_counter.py
|   |   +-- test_cost_calculator.py
|   |   +-- test_rate_limiter.py
|   |   +-- test_circuit_breaker.py
|   |   +-- test_cache.py
|   |   +-- test_guardrails.py
|   +-- integration/
|   |   +-- test_chat_endpoint.py
|   |   +-- test_health_endpoint.py
|   |   +-- test_completions_endpoint.py
|   +-- e2e/
|       +-- test_full_flow.py        # Docker-based full stack test (optional, Phase 5)
+-- infra/
|   +-- grafana/
|   |   +-- provisioning/
|   |   |   +-- dashboards/
|   |   |   |   +-- dashboard.yml    # Auto-provisioning config
|   |   |   |   +-- llm-ops.json     # Pre-built LLM operations dashboard
|   |   |   +-- datasources/
|   |   |       +-- prometheus.yml   # Auto-connect Prometheus to Grafana
|   +-- prometheus/
|       +-- prometheus.yml           # Scrape config targeting the app
+-- .env.example                     # All env vars with safe defaults and comments
+-- .pre-commit-config.yaml          # ruff, mypy, detect-secrets
+-- docker-compose.yml               # app + Redis + Prometheus + Grafana
+-- docker-compose.prod.yml          # Production overrides (no Grafana, resource limits)
+-- Dockerfile                       # Multi-stage build (builder + runtime)
+-- Makefile                         # dev, test, lint, build, up, down, logs
+-- pyproject.toml                   # Project metadata, dependencies, tool config
+-- README.md
+-- docs/
    +-- BRIEFING.md                  # This file
    +-- DECISIONS.md                 # Architecture Decision Records (generated during build)
```

---

## 7. API Contracts

### POST /v1/chat/completions

OpenAI-compatible chat completion endpoint.

**Request:**
```json
{
  "model": "gpt-4o-mini",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Explain circuit breakers in distributed systems."}
  ],
  "temperature": 0.7,
  "max_tokens": 500,
  "stream": false
}
```

**Response (non-streaming):**
```json
{
  "id": "req_abc123",
  "model": "gpt-4o-mini",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "A circuit breaker is a design pattern..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 28,
    "completion_tokens": 150,
    "total_tokens": 178,
    "estimated_cost_usd": 0.000089
  }
}
```

**Response (streaming, `"stream": true`):**
Server-Sent Events (SSE), each line:
```
data: {"choices": [{"delta": {"content": "A "}, "index": 0}]}
data: {"choices": [{"delta": {"content": "circuit "}, "index": 0}]}
...
data: {"choices": [{"delta": {}, "finish_reason": "stop", "index": 0}], "usage": {"prompt_tokens": 28, "completion_tokens": 150, "total_tokens": 178, "estimated_cost_usd": 0.000089}}
data: [DONE]
```

### POST /v1/completions

Simple prompt-in, text-out. Same structure as chat but with `"prompt"` instead of `"messages"`.

### GET /health

**Response (200):**
```json
{
  "status": "healthy",
  "checks": {
    "redis": "connected",
    "llm_provider": "reachable",
    "uptime_seconds": 3600
  },
  "version": "0.1.0"
}
```

### GET /health/ready

Kubernetes-style readiness probe. Returns 200 if the app can accept traffic, 503 if not.

### GET /metrics

Prometheus-format metrics exposition. Not JSON — raw Prometheus text format.

---

## 8. LLM-Specific Prometheus Metrics

Standard HTTP metrics (request count, latency histogram, error rate) are expected. These are the LLM-specific metrics that differentiate this template:

| Metric | Type | Labels | Purpose |
|--------|------|--------|---------|
| `llm_tokens_total` | Counter | model, direction (input/output), api_key | Total tokens processed |
| `llm_request_cost_usd` | Histogram | model, api_key | Cost distribution per request |
| `llm_cost_total_usd` | Counter | model, api_key | Cumulative cost |
| `llm_request_duration_seconds` | Histogram | model, stream (true/false) | End-to-end latency including LLM call |
| `llm_time_to_first_token_seconds` | Histogram | model | Streaming TTFT — key UX metric |
| `llm_cache_hits_total` | Counter | model | Cache effectiveness |
| `llm_cache_misses_total` | Counter | model | Cache misses |
| `llm_circuit_breaker_state` | Gauge | provider | 0=closed, 1=open, 2=half-open |
| `llm_rate_limit_rejected_total` | Counter | api_key | Rejected requests due to rate limiting |
| `llm_provider_errors_total` | Counter | provider, error_type | Provider-side errors (timeout, 429, 500) |

---

## 9. Grafana Dashboard

The pre-built dashboard (`infra/grafana/provisioning/dashboards/llm-ops.json`) must include these panels:

- **Request Rate** — requests/sec over time
- **Token Usage** — input vs output tokens over time, per model
- **Cost Tracker** — cumulative cost USD, per model, per API key
- **Latency Distribution** — p50, p95, p99 request duration
- **Time to First Token** — streaming TTFT distribution
- **Cache Hit Rate** — hits / (hits + misses) percentage
- **Circuit Breaker Status** — current state per provider
- **Error Rate** — 4xx vs 5xx breakdown
- **Rate Limit Rejections** — rejected requests over time
- **Active API Keys** — unique keys making requests

---

## 10. Non-Functional Requirements

| Category | Requirement |
|----------|------------|
| Startup | App must start and be ready in < 5 seconds (health check green) |
| Latency overhead | Template middleware adds < 5ms to each request (excluding LLM call) |
| Concurrent requests | Handle 50+ concurrent requests without degradation (Uvicorn workers) |
| Cache TTL | Default 1 hour, configurable per model via env |
| Rate limiting | Default 60 requests/minute per API key, configurable |
| Circuit breaker | Open after 5 consecutive failures, half-open after 30s, configurable |
| Docker image | Multi-stage build, final image < 200MB |
| Logging | JSON format, every request logged with: request_id, api_key (masked), model, tokens, cost, latency_ms |
| Secret management | No secrets in code or Docker image. `.env` for dev, environment variables for prod. Document Docker secrets integration |
| Security headers | CORS configurable, X-Request-ID propagated, no server version exposed |

---

## 11. Configuration (Pydantic Settings)

All configuration via environment variables. The `config.py` must define these with sensible defaults:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    app_name: str = "deployer"
    app_version: str = "0.1.0"
    environment: str = "development"   # development | staging | production
    debug: bool = False
    log_level: str = "INFO"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

    # Auth
    api_keys: list[str] = []           # Comma-separated in env: API_KEYS=key1,key2
    require_auth: bool = True

    # LLM Provider
    llm_provider: str = "openai"       # openai | anthropic
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    default_model: str = "gpt-4o-mini"
    request_timeout: int = 60

    # Rate Limiting
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60

    # Cache
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Circuit Breaker
    circuit_breaker_threshold: int = 5
    circuit_breaker_recovery_seconds: int = 30

    # CORS
    cors_origins: list[str] = ["*"]
```

---

## 12. Testing Strategy

### Coverage Target
Minimum 80% on core modules (llm/, middleware/). No coverage theater on boilerplate.

### What to Test

| Layer | What | Tool | Mock vs Real |
|-------|------|------|-------------|
| Unit | Token counter accuracy | pytest | Mock — no LLM calls |
| Unit | Cost calculator (model pricing tables) | pytest | Mock — pure logic |
| Unit | Rate limiter (window logic) | pytest + fakeredis | fakeredis — no real Redis |
| Unit | Circuit breaker (state transitions) | pytest | Mock — time-based |
| Unit | Cache key generation + hit/miss | pytest + fakeredis | fakeredis |
| Unit | Guardrails hooks (pre/post) | pytest | Mock |
| Integration | /v1/chat/completions (non-streaming) | pytest + httpx AsyncClient | Mock LLM provider, real FastAPI app |
| Integration | /v1/chat/completions (streaming SSE) | pytest + httpx AsyncClient | Mock LLM provider, validate SSE format |
| Integration | /health (deep check) | pytest + httpx AsyncClient | Mock Redis + provider reachability |
| Integration | Rate limiting rejection (429) | pytest + httpx AsyncClient | fakeredis |
| Integration | Auth rejection (401/403) | pytest + httpx AsyncClient | No mocks needed |
| E2E (optional) | Full Docker Compose stack | docker compose + curl/httpx | Real Redis, mock LLM provider |

### What NOT to Test
- Prometheus metrics exposition format (library responsibility)
- Grafana dashboard rendering
- Docker build correctness (CI builds it)
- Third-party library internals (httpx, structlog)

---

## 13. Key Engineering Decisions

These go in `docs/DECISIONS.md` and the README:

| Decision | Options Considered | Choice | Rationale |
|----------|--------------------|--------|-----------|
| API spec | Custom, OpenAI-compatible, LiteLLM proxy | OpenAI-compatible | Universal client compatibility, any OpenAI SDK works out of the box |
| Rate limiting | In-memory, Redis, API gateway | Redis sliding window | Distributed-ready, survives restarts, per-key granularity |
| Caching | No cache, exact match, semantic | Exact match (prompt hash) | Deterministic, simple, effective. Semantic cache is Phase 2 |
| Circuit breaker | None, tenacity, custom | Custom (minimal) | ~50 lines of code, no dependency for a simple state machine |
| Logging | logging stdlib, loguru, structlog | structlog | JSON output, context binding, processor pipeline, production standard |
| LLM client | langchain, litellm, direct httpx | Direct httpx | No framework lock-in, full control over streaming/retries/timeouts |
| Token counting | Estimate, tiktoken, provider response | tiktoken (pre) + provider (post) | Pre-request estimation for rate limiting, post-response actual for billing |
| Reverse proxy | Nginx, Traefik, None | None (in template) | Reduces complexity. Documented as optional production addition |
| Package manager | pip, poetry, uv | uv | Fast, modern, lockfile support, replaces pip + pip-tools |

---

## 14. What is Out of Scope

Keep scope tight. This is a portfolio template, not a platform:

- Frontend / UI — API-only, curl and SDK examples are enough
- User management / RBAC — API key auth only, no database-backed users
- Multi-tenant isolation — single-tenant template, mention multi-tenancy as extension point
- Fine-tuning / training — this is an inference proxy, not an ML pipeline
- Self-hosted model serving (vLLM, TGI) — this wraps external LLM APIs
- Database / ORM — no persistent storage beyond Redis cache
- WebSocket support — SSE streaming is sufficient
- Kubernetes manifests — Docker Compose only, mention K8s as production path in docs
- Automatic scaling — document how to scale, but do not implement auto-scaling
- Payment / billing integration — cost tracking is observability, not billing
- PII detection implementation — guardrails hooks are extensible placeholders, not implementations

---

## 15. Commit Plan (Incremental)

Each commit = a working state. No broken commits.

### Phase 1 — Foundation
```
feat: initialize project structure with pyproject.toml and Makefile
feat: add pydantic-settings config with env support and .env.example
feat: add Docker and docker-compose with Redis service
feat: add structlog configuration with JSON output
```

### Phase 2 — Core Middleware
```
feat: add request ID middleware with X-Request-ID propagation
feat: add structured request/response logging middleware
feat: add API key authentication middleware
feat: add Redis-backed sliding window rate limiter
test: add unit tests for rate limiter with fakeredis
test: add integration tests for auth and rate limiting (401, 403, 429)
```

### Phase 3 — LLM Service Layer
```
feat: add abstract LLM provider interface
feat: add OpenAI provider implementation with streaming support
feat: add Anthropic provider implementation with streaming support
feat: add tiktoken-based token counter
feat: add model-aware cost calculator
test: add unit tests for token counter and cost calculator
```

### Phase 4 — API Endpoints
```
feat: add /v1/chat/completions endpoint (non-streaming)
feat: add /v1/chat/completions streaming via SSE
feat: add /v1/completions endpoint
feat: add deep /health and /health/ready endpoints
test: add integration tests for chat completions (mock provider)
test: add integration tests for streaming SSE format validation
test: add integration tests for health endpoints
```

### Phase 5 — Resilience
```
feat: add response cache with Redis and prompt hashing
feat: add circuit breaker for LLM provider calls
feat: add guardrails hooks (pre/post processing extensible interface)
test: add unit tests for cache, circuit breaker, and guardrails
```

### Phase 6 — Observability
```
feat: add Prometheus metrics with LLM-specific counters and histograms
feat: add /metrics endpoint for Prometheus scraping
feat: add Prometheus service to docker-compose with scrape config
feat: add Grafana service with auto-provisioned datasource and dashboard
feat: add pre-built Grafana LLM operations dashboard JSON
```

### Phase 7 — CI/CD and Polish
```
ci: add GitHub Actions workflow for lint, type check, and test
feat: add pre-commit config with ruff, mypy, and detect-secrets
feat: add multi-stage Dockerfile for optimized production image
feat: add docker-compose.prod.yml with production overrides
docs: add README with problem statement, architecture, quickstart, and decisions
docs: add DECISIONS.md with architecture decision records
```

---

## 16. README Structure

The README must follow this structure:

1. **One-liner** — what this is in one sentence
2. **Problem** — why this exists (3 sentences max)
3. **Architecture diagram** — Mermaid diagram showing request flow
4. **Quickstart** — `git clone` -> `cp .env.example .env` -> `docker compose up` -> `curl /v1/chat/completions`
5. **Configuration** — table of key environment variables with defaults
6. **API Reference** — endpoints with curl examples
7. **LLM-Specific Features** — what makes this different from a generic FastAPI template
8. **Observability** — how to access Grafana, what metrics are tracked
9. **Technical Decisions** — table format (decision, options, choice, rationale)
10. **Project Structure** — tree view
11. **Testing** — how to run tests, what is covered
12. **Production Considerations** — what to add for real production (Nginx, K8s, secrets vault)
13. **License** — MIT

---

## 17. Implementation Guidelines for the Agent

1. **Read this entire briefing before writing any code.**

2. **Incremental, atomic commits.** Each commit is a complete, working unit. Never accumulate work and commit at the end. The commit history is part of the deliverable and must reflect a professional, reviewable progression.

3. **Tests accompany features.** Every new module or feature must have its tests committed in the same phase, before moving to the next phase. Do not defer tests.

4. **Conventional Commits for all messages.** Format: `type: description`. Types: `feat`, `fix`, `test`, `docs`, `ci`, `refactor`, `chore`. Scope is optional but encouraged for large phases (e.g., `feat(middleware): add rate limiter`).

5. **Minimal code, maximum clarity.** Functions over classes unless state is genuinely needed. No abstract factories, no enterprise patterns. If a module is under 100 lines, it is probably the right size.

6. **Type hints on everything.** All function signatures, return types, and variable annotations where non-obvious. Use `mypy --strict` as the target.

7. **No framework abstractions.** Use httpx directly for LLM calls, not LangChain or LiteLLM. The template must be understandable by reading the code, not by reading framework docs.

8. **Configuration via environment.** No hardcoded values. Every tunable parameter lives in `config.py` with a sensible default. If you are writing a magic number, it belongs in config.

9. **Docker Compose must work on first `docker compose up`.** No manual setup steps beyond copying `.env.example`. Redis, Prometheus, and Grafana must auto-configure.

10. **Error messages must be actionable.** "Connection refused" is bad. "Redis connection failed at redis://localhost:6379 — is the Redis container running?" is good.

11. **Logging context.** Every log line in the request path must include: request_id, api_key (last 4 chars only), model, and relevant operation. Use structlog context binding.

12. **The Grafana dashboard must work without manual configuration.** Auto-provisioning via mounted config files. On `docker compose up`, Grafana should already have the datasource connected and the dashboard loaded.

---

## 18. Success Criteria

The project is done when:

- [ ] `docker compose up` starts app + Redis + Prometheus + Grafana with zero manual config
- [ ] `curl -H "X-API-Key: test-key" -X POST /v1/chat/completions` returns a valid response (with mock or real provider)
- [ ] Streaming SSE works with `curl --no-buffer`
- [ ] Rate limiting returns 429 after exceeding configured threshold
- [ ] Unauthenticated requests return 401
- [ ] `/health` returns deep check status for Redis and LLM provider
- [ ] `/metrics` exposes LLM-specific Prometheus metrics
- [ ] Grafana dashboard at `localhost:3000` shows live panels with data
- [ ] `make test` passes with 80%+ coverage on core modules
- [ ] `make lint` passes (ruff + mypy)
- [ ] GitHub Actions pipeline runs lint + test + Docker build on push
- [ ] README explains architecture, quickstart, decisions, and production considerations
- [ ] Commit history shows clean, incremental, reviewable progression
