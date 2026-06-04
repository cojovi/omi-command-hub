#!/usr/bin/env bash
set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <backup.sql>"
  exit 1
fi

cd "$(dirname "$0")/.."
docker exec -i omi_postgres psql -U omi_user -d omi_command_hub < "$1"
echo "Restore complete from $1"
