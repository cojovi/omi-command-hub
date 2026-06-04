#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."
BACKUP_DIR="./backups"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
docker exec omi_postgres pg_dump -U omi_user omi_command_hub > "$BACKUP_DIR/omi_command_hub_$TIMESTAMP.sql"

echo "Backup created: $BACKUP_DIR/omi_command_hub_$TIMESTAMP.sql"
