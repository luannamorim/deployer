# ─────────────────────────────────────────────
# Stage 1: builder — install dependencies
# ─────────────────────────────────────────────
FROM python:3.12.10-slim AS builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.11.6 /uv /usr/local/bin/uv

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./
COPY README.md ./

# Install only production dependencies (no dev extras)
RUN uv sync --frozen --no-dev

# ─────────────────────────────────────────────
# Stage 2: runtime — minimal production image
# ─────────────────────────────────────────────
FROM python:3.12.10-slim AS runtime

WORKDIR /app

# Create non-root user
RUN groupadd --gid 1001 deployer && \
    useradd --uid 1001 --gid deployer --shell /bin/bash --no-create-home deployer

# Copy the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application source
COPY src/ ./src/

# Ensure the venv is on PATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

LABEL org.opencontainers.image.title="deployer" \
      org.opencontainers.image.description="Production-ready deploy template for LLM applications" \
      org.opencontainers.image.licenses="MIT"

USER deployer

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/ready')" || exit 1

# WORKERS controls uvicorn worker count. Default 1 for dev; set to (2*CPU+1) in production.
ENV WORKERS=1

CMD exec uvicorn deployer.main:app --host 0.0.0.0 --port 8000 --workers ${WORKERS}
