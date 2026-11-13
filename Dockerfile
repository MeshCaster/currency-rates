# syntax=docker/dockerfile:1.7
# Multi-stage build with uv. Pin the uv tag (e.g. ghcr.io/astral-sh/uv:0.9.x) for reproducible builds.

# ---------- build stage: resolve and install dependencies into /app/.venv
FROM python:3.14-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

# Extras to bake into the image, e.g. "--extra postgres --extra otel"
ARG UV_EXTRAS="--extra postgres --extra otel"

WORKDIR /app

# 1) third-party dependencies only: this layer is cached until uv.lock changes. uv needs every
#    workspace member's pyproject.toml to resolve, but none of their code yet.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev ${UV_EXTRAS}

# 2) the project and its workspace packages (packages/*)
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev ${UV_EXTRAS}

# ---------- runtime stage: no uv, no build tools, non-root user
FROM python:3.14-slim AS runtime

RUN groupadd --system app && useradd --system --gid app --no-create-home app
WORKDIR /app
COPY --from=builder --chown=app:app /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production

USER app
EXPOSE 8000

# The health check follows APP_ROLE: /health/live for the API, the heartbeat file for the worker.
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
    CMD ["/app/docker/healthcheck.sh"]

# One process per container; scale with replicas. Use --workers N only on a plain VM.
# APP_ROLE=api (default) migrates and serves HTTP; APP_ROLE=worker runs the background jobs.
# See docker/entrypoint.sh.
ENTRYPOINT ["/app/docker/entrypoint.sh"]
