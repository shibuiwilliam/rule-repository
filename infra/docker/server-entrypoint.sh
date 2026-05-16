#!/bin/bash
set -euo pipefail

echo "Running Alembic migrations..."
python -m alembic upgrade head
echo "Migrations complete."

echo "Starting server..."
exec "$@"
