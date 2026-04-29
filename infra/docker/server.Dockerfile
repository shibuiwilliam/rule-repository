FROM python:3.13-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy workspace root files needed for dependency resolution
COPY pyproject.toml /app/pyproject.toml
COPY uv.lock /app/uv.lock
COPY apps/server/pyproject.toml /app/apps/server/pyproject.toml
COPY packages/rule-client/pyproject.toml /app/packages/rule-client/pyproject.toml
COPY packages/agentic-client/pyproject.toml /app/packages/agentic-client/pyproject.toml
COPY packages/cli/pyproject.toml /app/packages/cli/pyproject.toml

# Create stub packages so uv workspace resolves
RUN mkdir -p /app/apps/server/src/rulerepo_server && \
    touch /app/apps/server/src/rulerepo_server/__init__.py && \
    mkdir -p /app/packages/rule-client/src/rulerepo && \
    touch /app/packages/rule-client/src/rulerepo/__init__.py && \
    mkdir -p /app/packages/agentic-client/src/rulerepo_agentic && \
    touch /app/packages/agentic-client/src/rulerepo_agentic/__init__.py && \
    mkdir -p /app/packages/cli/src/rulerepo_cli && \
    touch /app/packages/cli/src/rulerepo_cli/__init__.py

# Install the server package and its dependencies into the workspace venv
RUN uv sync --frozen --package rulerepo-server --no-dev 2>/dev/null || \
    uv sync --package rulerepo-server --no-dev

# ---- Runtime stage ----
FROM python:3.13-slim

WORKDIR /app

# Copy the virtual environment from builder (created at workspace root)
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src"

# Copy server source code
COPY apps/server/src /app/src
COPY apps/server/alembic.ini /app/alembic.ini
COPY apps/server/alembic /app/alembic

# Copy entrypoint
COPY infra/docker/server-entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "rulerepo_server.main:app", "--host", "0.0.0.0", "--port", "8000"]
