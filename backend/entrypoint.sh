#!/bin/sh
set -e

alembic upgrade head

if [ "${SEED_ON_START}" = "true" ]; then
    python -m app.seed.seeder || echo "[entrypoint] seed failed (continuing)"
fi

if [ -n "${ADMIN_EMAIL}" ] && [ -n "${ADMIN_PASSWORD}" ]; then
    python -m app.seed.create_admin || echo "[entrypoint] admin creation failed (continuing)"
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
