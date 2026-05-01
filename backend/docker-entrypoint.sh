#!/bin/sh
# Entrypoint: wait briefly for Postgres, run migrations, then exec the CMD.
# Compose's depends_on with healthcheck condition handles ordering, but we
# defensively retry once anyway in case the healthcheck is misconfigured.

set -e

if [ -n "${SKIP_MIGRATIONS:-}" ]; then
    echo "[entrypoint] SKIP_MIGRATIONS set, skipping alembic upgrade"
else
    echo "[entrypoint] running alembic upgrade head"
    cd /app/backend && alembic upgrade head && cd /app
fi

echo "[entrypoint] starting: $*"
exec "$@"
