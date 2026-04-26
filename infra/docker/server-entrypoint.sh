#!/bin/bash
set -euo pipefail

echo "Running Alembic migrations..."
python -m alembic upgrade head || echo "Warning: Alembic migrations failed (may not exist yet)"

echo "Starting server..."
exec "$@"
