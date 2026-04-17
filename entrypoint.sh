#!/bin/sh
# entrypoint.sh — LogSentinel container startup
#
# Runs alembic migrations with explicit exit-code checking before handing off
# to uvicorn. Every step is logged to stdout so Railway captures it verbatim.
# PYTHONUNBUFFERED=1 is already set in the Dockerfile, but we force it here
# too so this script can never silently swallow output.

export PYTHONUNBUFFERED=1

echo "=== LogSentinel startup ==="
echo "Timestamp : $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "Python    : $(python --version 2>&1)"
echo "Port      : ${PORT:-8000}"
echo "DATABASE_URL set: $([ -n "$DATABASE_URL" ] && echo yes || echo NO — migrations will fail)"
echo ""

# ---------------------------------------------------------------------------
# 1. Alembic migrations
# ---------------------------------------------------------------------------
echo "--- Running: alembic upgrade head ---"
alembic upgrade head
ALEMBIC_EXIT=$?

echo ""
echo "--- alembic exited with code: ${ALEMBIC_EXIT} ---"

if [ "${ALEMBIC_EXIT}" -ne 0 ]; then
    echo "ERROR: alembic upgrade head failed (exit ${ALEMBIC_EXIT}). Aborting startup." >&2
    exit "${ALEMBIC_EXIT}"
fi

echo "Migrations applied successfully."
echo ""

# ---------------------------------------------------------------------------
# 2. Uvicorn
# ---------------------------------------------------------------------------
echo "--- Starting uvicorn on 0.0.0.0:${PORT:-8000} ---"
exec uvicorn api.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --log-level info
