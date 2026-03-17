#!/usr/bin/env bash
# Docker entrypoint — waits for FalkorDB and optionally seeds demo data.
set -e

echo "🔴 RedThread — Starting up..."

# Wait for FalkorDB to be ready (the depends_on healthcheck handles most of
# this, but a brief poll ensures the graph module is loaded).
MAX_RETRIES=30
RETRY=0
until redis-cli -h "${FALKORDB_HOST:-localhost}" -p "${FALKORDB_PORT:-6379}" ping 2>/dev/null | grep -q PONG; do
    RETRY=$((RETRY + 1))
    if [ "$RETRY" -ge "$MAX_RETRIES" ]; then
        echo "⚠️  FalkorDB not reachable after ${MAX_RETRIES} attempts — starting anyway"
        break
    fi
    echo "⏳ Waiting for FalkorDB... (${RETRY}/${MAX_RETRIES})"
    sleep 1
done

# Seed demo data on first run (when the marker file does not exist)
SEED_MARKER="/app/data/.seeded"
if [ "${SEED_DATA:-true}" = "true" ] && [ ! -f "$SEED_MARKER" ]; then
    echo "🌱 Seeding demo data (first run)..."
    python -m src.seed && touch "$SEED_MARKER"
    echo "✅ Demo data loaded"
elif [ -f "$SEED_MARKER" ]; then
    echo "📌 Seed marker found — skipping seed"
fi

echo "🚀 Starting RedThread server..."
exec "$@"
