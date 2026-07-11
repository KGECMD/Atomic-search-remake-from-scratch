#!/bin/bash
# SuperNova Search Start Script

set -e

# Get port from Railway or default to 8080
PORT="${PORT:-8080}"

echo "Starting SuperNova Search on port $PORT..."

exec python -m gunicorn \
    atomic_search.app:app \
    --bind "0.0.0.0:$PORT" \
    --workers 2 \
    --threads 4 \
    --access-logfile - \
    --error-logfile -
