#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

docker compose build
docker compose up -d

docker compose exec -T api alembic upgrade head 2>/dev/null || \
  docker compose run --rm api alembic upgrade head

docker compose ps
docker compose logs --tail=50 api
