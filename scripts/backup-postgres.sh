#!/bin/sh
# Daily Postgres backup — gzipped pg_dump rotated by date.
# Mount onto the postgres container at /usr/local/bin/backup-postgres.sh
# and trigger via cron on the host:
#
#   0 3 * * * docker exec ki-berater-postgres-1 sh /usr/local/bin/backup-postgres.sh
#
# Backups land in /var/lib/postgresql/backups inside the volume.

set -e

BACKUP_DIR=/var/lib/postgresql/backups
KEEP_DAYS=${KEEP_DAYS:-14}
TS=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -Z 6 -f "$BACKUP_DIR/ki_${TS}.dump"

# Rotate.
find "$BACKUP_DIR" -type f -name "ki_*.dump" -mtime +$KEEP_DAYS -delete

echo "[backup] wrote $BACKUP_DIR/ki_${TS}.dump (kept ${KEEP_DAYS} days)"
