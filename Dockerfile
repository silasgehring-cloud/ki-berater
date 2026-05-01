# syntax=docker/dockerfile:1.7

# ----- builder -----
FROM python:3.14-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

# System libs needed only for build (asyncpg ships wheels, but cffi/cryptography may not).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install runtime deps into an isolated path that we'll copy into the final stage.
COPY pyproject.toml ./
RUN pip install --prefix=/install \
    "fastapi>=0.115" \
    "uvicorn[standard]>=0.32" \
    "pydantic>=2.9" \
    "pydantic-settings>=2.6" \
    "sqlalchemy[asyncio]>=2.0" \
    "asyncpg>=0.30" \
    "alembic>=1.14" \
    "structlog>=24.4" \
    "redis>=5.2" \
    "httpx>=0.27" \
    "argon2-cffi>=23.1" \
    "slowapi>=0.1.9" \
    "anthropic>=0.39" \
    "google-genai>=0.3" \
    "qdrant-client>=1.12"

# ----- runtime -----
FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000

# libpq for asyncpg, curl for in-image healthchecks.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        tini \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash --uid 1000 appuser

COPY --from=builder /install /usr/local

WORKDIR /app
COPY backend ./backend
COPY pyproject.toml ./

# Drop root.
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Liveness check — independent of DB readiness so docker can detect zombie procs.
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

# tini reaps children + forwards signals correctly to uvicorn workers.
ENTRYPOINT ["/usr/bin/tini", "--", "/app/backend/docker-entrypoint.sh"]
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
