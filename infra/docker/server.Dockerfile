FROM python:3.13-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy workspace root pyproject.toml and server pyproject.toml for dependency resolution
COPY pyproject.toml /app/pyproject.toml
COPY apps/server/pyproject.toml /app/apps/server/pyproject.toml

# Create stub packages so uv workspace resolves
RUN mkdir -p /app/apps/server/src/rulerepo_server && \
    touch /app/apps/server/src/rulerepo_server/__init__.py && \
    mkdir -p /app/packages/rule-client/src/rulerepo && \
    touch /app/packages/rule-client/src/rulerepo/__init__.py && \
    mkdir -p /app/packages/agentic-client/src/rulerepo_agentic && \
    touch /app/packages/agentic-client/src/rulerepo_agentic/__init__.py

# Create minimal pyproject.toml for stub packages
RUN echo '[project]\nname = "rulerepo"\nversion = "0.1.0"\nrequires-python = ">=3.13"\n\n[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n\n[tool.hatch.build.targets.wheel]\npackages = ["src/rulerepo"]' > /app/packages/rule-client/pyproject.toml && \
    echo '[project]\nname = "rulerepo-agentic"\nversion = "0.1.0"\nrequires-python = ">=3.13"\n\n[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n\n[tool.hatch.build.targets.wheel]\npackages = ["src/rulerepo_agentic"]' > /app/packages/agentic-client/pyproject.toml

# Install dependencies
RUN cd /app/apps/server && uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev

# ---- Runtime stage ----
FROM python:3.13-slim

WORKDIR /app

# Copy the virtual environment from builder
COPY --from=builder /app/apps/server/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

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
