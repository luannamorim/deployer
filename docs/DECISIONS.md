# Architecture Decision Records

This document records the key architectural decisions made during the development of `deployer`, along with the alternatives considered and the rationale for each choice.

---

## ADR-001: OpenAI-Compatible API Spec

**Status:** Accepted

**Context:** The proxy needs an API contract. Options were a custom schema, the OpenAI spec, or using LiteLLM as a proxy-of-proxy.

**Decision:** Follow the OpenAI `/v1/chat/completions` and `/v1/completions` specs exactly.

**Rationale:** Any client that works with OpenAI (SDK, curl, LangChain, LlamaIndex) works with this template without modification. Switching the backing provider (OpenAI → Anthropic) is a config change, not a client change. A custom schema would require every consumer to update their client. LiteLLM as a dependency adds another abstraction layer and its own update cycle.

**Consequences:** We must maintain OpenAI field names and response shapes even when they are verbose. The Anthropic provider adapter translates at the boundary.

---

## ADR-002: Direct httpx for LLM Calls

**Status:** Accepted

**Context:** Calling LLM APIs requires HTTP. Options: LangChain, LiteLLM, direct httpx.

**Decision:** Direct httpx with a thin provider abstraction (`LLMProvider` ABC).

**Rationale:** LangChain and LiteLLM are large dependencies with their own release cycles, breaking changes, and abstractions. The template needs to be readable by reading the code, not by reading framework docs. httpx is already a project dependency for testing; using it directly adds no new dependency. The provider abstraction (`base.py` + `openai.py` + `anthropic.py`) is ~300 lines total — fully understandable in one reading.

**Consequences:** We own the retry, timeout, and streaming logic. This is a feature, not a burden — the template explicitly shows how these work.

---

## ADR-003: Redis for Both Caching and Rate Limiting

**Status:** Accepted

**Context:** The template needs a cache and a rate limiter. Both need external state to survive restarts.

**Decision:** Use Redis for both, with a single Redis service in Docker Compose.

**Rationale:** Redis is already a common dependency in production LLM workloads. Using it for both avoids adding a second stateful service. The sliding window rate limiter uses a sorted set (ZREMRANGEBYSCORE + ZCARD + ZADD), which is a well-understood Redis pattern. The cache uses simple GET/SET with TTL. Both share the same connection pool.

**Consequences:** Redis is a required dependency. The Docker Compose setup includes Redis with health checks. Production deployments should use a managed Redis (ElastiCache, Upstash) rather than a container.

---

## ADR-004: Exact-Match Response Cache

**Status:** Accepted

**Context:** Caching LLM responses requires a cache key strategy. Options: exact match (deterministic hash), semantic similarity (vector search), or no cache.

**Decision:** SHA-256 hash of (model, messages, temperature, max_tokens) as a deterministic cache key.

**Rationale:** Semantic caching (via embeddings and vector search) requires a vector database, an embedding model call on every request, and a similarity threshold that is hard to tune. Exact match is deterministic, requires no extra infrastructure, and handles the most valuable case: repeated identical queries (e.g., templated prompts, eval runs). Semantic caching is a natural Phase 2 extension.

**Consequences:** Cache hit rate will be lower than semantic caching for paraphrased queries. Temperature must be included in the key — two requests with different temperatures should not share a cached response.

---

## ADR-005: Custom Circuit Breaker

**Status:** Accepted

**Context:** LLM providers have outages. The app needs to fail fast rather than pile up hanging requests. Options: `tenacity` library, `circuitbreaker` library, custom implementation.

**Decision:** Custom circuit breaker in ~50 lines (`circuit_breaker.py`).

**Rationale:** The circuit breaker state machine (CLOSED → OPEN → HALF_OPEN → CLOSED) is well-defined and small. Adding `tenacity` or `circuitbreaker` as a dependency for this logic would be overkill. The custom implementation is fully transparent — every state transition is visible in the code. It uses `time.monotonic()` for recovery timing and supports async callables via `ParamSpec`.

**Consequences:** We own the implementation. Tests cover all state transitions (8 test cases). If requirements grow (e.g., per-error-type thresholds), the implementation can be extended.

---

## ADR-006: structlog over stdlib logging

**Status:** Accepted

**Context:** Production LLM applications need structured, searchable logs. Options: stdlib `logging`, `loguru`, `structlog`.

**Decision:** structlog with JSON output in production, colored console output in development.

**Rationale:** structlog supports context binding via `contextvars`, which allows request-scoped fields (request_id, api_key) to be automatically included in every log line within a request without threading through parameters. stdlib logging has no built-in context binding. loguru is good but less common in enterprise Python. structlog is the production standard for structured Python logging and outputs valid JSON that ingests cleanly into log aggregators (Loki, Datadog, CloudWatch).

**Consequences:** Log format switches between TTY (colored, human-readable) and non-TTY (JSON) based on `sys.stdout.isatty()`. All log lines in the request path include: request_id, api_key (last 4 chars), model, tokens, cost, latency_ms.

---

## ADR-007: tiktoken for Pre-Request Token Counting

**Status:** Accepted

**Context:** Token counting is needed for rate limiting and cost estimation before the LLM response arrives.

**Decision:** tiktoken for pre-request estimation; provider response for post-request actual count.

**Rationale:** tiktoken gives accurate token counts without making an API call. This enables per-token rate limiting before the LLM call, and early cost estimation for logging. Post-request, the provider returns the actual token counts (which may differ slightly from tiktoken estimates for Anthropic). The actual counts are used for billing metrics. tiktoken is already used by OpenAI's own libraries and is reliable for OpenAI models; for Anthropic it falls back to approximate counting.

**Consequences:** tiktoken is a production dependency (~2MB). Token estimates may vary slightly from actual counts for non-OpenAI models.

---

## ADR-008: No Reverse Proxy in Template

**Status:** Accepted

**Context:** Production deployments typically put a reverse proxy (Nginx, Traefik) in front of the application server.

**Decision:** No reverse proxy in the template. FastAPI + Uvicorn serve traffic directly.

**Rationale:** Adding Nginx adds operational complexity (config, health checks, TLS certs) that is not LLM-specific and would distract from the template's purpose. Uvicorn is production-grade for most workloads. The template documents Nginx/Traefik as the standard production addition but does not prescribe it — teams use different proxies (Traefik on K8s, AWS ALB, Cloudflare).

**Consequences:** TLS termination must be handled at a higher layer (load balancer, ingress controller). The `CORS_ORIGINS` config handles browser security at the application layer.

---

## ADR-009: uv as Package Manager

**Status:** Accepted

**Context:** Python package management options: pip + pip-tools, poetry, uv.

**Decision:** uv with `pyproject.toml` and `uv.lock`.

**Rationale:** uv is 10-100x faster than pip for dependency resolution and installation. It replaces pip, pip-tools, virtualenv, and parts of poetry in one tool. The lockfile (`uv.lock`) is deterministic and CI-friendly. uv is now the standard choice for new Python projects in 2024-2025. poetry is slower and has historically had resolver issues with complex dependency trees.

**Consequences:** Contributors need uv installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`). The Dockerfile copies uv from the official image rather than installing it via pip.

---

## ADR-010: Prometheus + Grafana for Observability

**Status:** Accepted

**Context:** The template needs an observability stack. Options: OpenTelemetry, Datadog agent, Prometheus + Grafana, logging-only.

**Decision:** Prometheus for metrics collection, Grafana for visualization, both auto-provisioned via Docker Compose.

**Rationale:** Prometheus + Grafana is the open-source standard for metrics observability and requires no external accounts or API keys. The entire stack runs locally with `docker compose up`. The pre-built dashboard JSON (`llm-operations.json`) auto-loads with panels for every LLM-specific metric. For production, teams can swap to a managed stack (Grafana Cloud, Datadog) while keeping the same Prometheus metrics endpoint — the `/metrics` format is universal.

**Consequences:** Two additional services in Docker Compose (prometheus, grafana). The dashboard JSON must be maintained when new metrics are added. The `docker-compose.prod.yml` override places Grafana behind a profile so production deployments can opt out.
