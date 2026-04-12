# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`deployer` is a production-ready deploy template for LLM applications. It's an OpenAI-compatible API proxy built with FastAPI that adds token counting, cost tracking, rate limiting, caching, circuit breaking, and observability on top of LLM provider calls (OpenAI, Anthropic). Not a generic FastAPI boilerplate — every feature exists because LLM workloads have specific operational needs.

## Build & Development Commands

```bash
make dev          # Start development server
make test         # Run all tests
make lint         # Run ruff + mypy
make build        # Build Docker image
make up           # docker compose up (app + Redis + Prometheus + Grafana)
make down         # docker compose down
make logs         # Tail container logs
```

Run a single test file:
```bash
uv run pytest tests/unit/test_token_counter.py -v
```

Run tests with coverage:
```bash
uv run pytest --cov=src/deployer tests/
```

Before committing, always run `make lint` and `make test` — both must pass.

## Architecture

```
Client → FastAPI App → Middleware Stack → Router → LLM Service Layer → LLM Provider (OpenAI/Anthropic)
                           ↓                            ↓
                    Auth, Rate Limit,             Token Counter,
                    Request ID, Logging           Cost Calculator,
                                                  Cache (Redis),
                                                  Circuit Breaker,
                                                  Guardrails Hooks
                                                       ↓
                                                 Observability
                                                 (structlog, Prometheus, Grafana)
```

- **`src/deployer/main.py`** — FastAPI app factory with lifespan events
- **`src/deployer/config.py`** — Pydantic Settings, all config via env vars
- **`src/deployer/middleware/`** — Auth (API key), rate limiting (Redis sliding window), request ID, structured logging
- **`src/deployer/api/v1/`** — Routes: `/v1/chat/completions`, `/v1/completions`, `/health`, `/health/ready`
- **`src/deployer/llm/`** — Provider abstraction (base → openai/anthropic), token counter (tiktoken), cost calculator, Redis cache, circuit breaker, guardrails hooks
- **`src/deployer/observability/`** — structlog config, Prometheus metrics (LLM-specific: tokens, cost, TTFT, cache hits, circuit breaker state)
- **`src/deployer/dependencies.py`** — FastAPI dependency injection for Redis, provider, etc.

## Key Design Decisions

- **Direct httpx** for LLM calls — no LangChain/LiteLLM. Full control over streaming/retries/timeouts.
- **uv** as package manager (fast, lockfile support)
- **OpenAI-compatible API** — `/v1/chat/completions` follows OpenAI spec so any OpenAI SDK client works
- **Redis** for both caching and rate limiting (sliding window)
- **Custom circuit breaker** (~50 lines) rather than a dependency
- **tiktoken** for pre-request token estimation, provider response for post-request actual count

## Tech Stack

FastAPI, Uvicorn, pydantic-settings, Redis, structlog, prometheus-client, httpx, tiktoken, ruff, mypy, pytest + pytest-asyncio + fakeredis, Docker + Docker Compose, GitHub Actions

## Testing Patterns

- Unit tests use **fakeredis** for Redis-dependent code (rate limiter, cache)
- Integration tests use **httpx AsyncClient** with mock LLM providers against real FastAPI app
- Target 80%+ coverage on `llm/` and `middleware/`
- Tests accompany features in the same commit phase

## Commit Conventions

- Conventional Commits: `type(scope): description` (lowercase, imperative, no period)
- Types: `feat`, `fix`, `test`, `docs`, `ci`, `refactor`, `chore`
- Follow the phased commit plan in `docs/BRIEFING.md` section 15
- Each commit = one logical unit of work, project must be in working state

## Docker

- Multi-stage build: builder for deps, runtime on `python:3.12-slim`
- Run as non-root user
- `docker compose up` must work with zero manual config (Redis, Prometheus, Grafana auto-provision)
- Ports: app (8000), Grafana (3000), Prometheus (9090)
