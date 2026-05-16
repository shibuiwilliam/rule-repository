#!/bin/bash
set -euo pipefail

echo "Running Alembic migrations..."
if python -m alembic upgrade head; then
    echo "Migrations complete."
else
    echo "ERROR: Alembic migrations failed. Check the migration chain and database state."
    echo "The server will NOT start until migrations succeed."
    echo "To debug: docker compose exec server python -m alembic history"
    exit 1
fi

echo "Starting server..."
exec "$@"
