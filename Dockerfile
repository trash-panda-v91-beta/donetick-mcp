# syntax=docker/dockerfile:1

# Build stage: install runtime deps and the project into a virtualenv.
FROM python:3.14-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /uvx /bin/

# Use the image's system Python; don't pull dev/test deps into the image.
ENV UV_PYTHON_DOWNLOADS=0 \
    UV_NO_DEV=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Cache dependency install (they change rarely vs. project source).
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-editable

# Copy the project and install it (non-editable, so the code lives in .venv).
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable

# Runtime stage: copy only the virtualenv.
FROM python:3.14-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN useradd -m -u 1000 mcpuser
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
USER mcpuser

# MCP stdio server entrypoint.
CMD ["/app/.venv/bin/donetick-mcp"]
