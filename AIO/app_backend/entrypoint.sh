#!/bin/sh
set -e

echo "Waiting for Postgres..."
# A simple retry loop rather than a fixed sleep — docker-compose's
# depends_on only waits for the container to START, not for Postgres to
# actually be ready to accept connections, which is a common source of
# "connection refused" on first boot.
until python -c "
import asyncio, asyncpg, os, sys
async def check():
    try:
        conn = await asyncpg.connect(os.environ['DATABASE_URL'].replace('postgresql+asyncpg', 'postgresql'))
        await conn.close()
    except Exception:
        sys.exit(1)
asyncio.run(check())
"; do
  echo "Postgres not ready yet, retrying in 2s..."
  sleep 2
done

echo "Running migrations..."
alembic upgrade head

echo "Starting server..."
# Runs whatever CMD/`command:` was passed in, defaulting (via the
# Dockerfile's CMD) to plain uvicorn. This lets docker-compose.override.yml
# swap in `--reload` for local dev without needing a second entrypoint.
exec "$@"
