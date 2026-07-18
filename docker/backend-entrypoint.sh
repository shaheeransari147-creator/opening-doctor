#!/bin/sh
set -e

if [ -z "$DATABASE_URL" ]; then
  # Docker Compose case: Postgres is a sibling container that might not have
  # finished starting yet. A managed host (DATABASE_URL set, e.g. Neon on
  # Render) is already up by definition, so this wait is skipped there.
  echo "Waiting for Postgres at ${POSTGRES_HOST:-postgres}:${POSTGRES_PORT:-5432}..."
  until python -c "
import socket, os, sys
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2)
try:
    s.connect((os.environ.get('POSTGRES_HOST', 'postgres'), int(os.environ.get('POSTGRES_PORT', 5432))))
    sys.exit(0)
except OSError:
    sys.exit(1)
"; do
    sleep 1
  done
  echo "Postgres is up."
fi

echo "Running Alembic migrations..."
alembic upgrade head

echo "Seeding ECO opening book (idempotent, upserts only new rows)..."
python -m database.seed.load_opening_book

echo "Indexing knowledge base into Qdrant (checksum-gated, cheap no-op if unchanged;
this also rebuilds the local Qdrant index from scratch on hosts with ephemeral disk,
e.g. Render's free tier, since it isn't persisted across deploys/restarts there)..."
python -m database.seed.index_knowledge_base

if [ "$SEED_DEMO_DATA" = "true" ]; then
  # Opt-in, not idempotent (re-inserts the same games as new rows each time)
  # -- meant for the first boot only on hosts without shell access (e.g.
  # Render's free tier). Unset this env var after the first successful
  # deploy so restarts don't keep duplicating the demo games.
  echo "SEED_DEMO_DATA=true: loading sample games (remove this env var after first boot)..."
  python -m database.seed.seed_games
fi

echo "Starting API..."
exec "$@"
