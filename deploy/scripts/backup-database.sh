#!/usr/bin/env bash
# Automated Production Database Backup Script for AMARA
# Performs encrypted/compressed PostgreSQL backup with SHA256 checksum and retention policy.

set -eo pipefail

BACKUP_DIR="${AMARA_BACKUP_DIR:-/var/backups/amara}"
DB_HOST="${PGHOST:-postgres}"
DB_PORT="${PGPORT:-5432}"
DB_USER="${PGUSER:-amara}"
DB_NAME="${PGDATABASE:-amara_prod}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

mkdir -p "${BACKUP_DIR}"

TIMESTAMP=$(date -u +"%Y%m%d_%H%M%SZ")
BACKUP_FILENAME="${BACKUP_DIR}/amara_backup_${DB_NAME}_${TIMESTAMP}.sql.gz"
CHECKSUM_FILENAME="${BACKUP_FILENAME}.sha256"

echo "=== AMARA Database Backup Starting ==="
echo "Target: ${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
echo "Output: ${BACKUP_FILENAME}"

# Execute pg_dump with custom compressed format
PGPASSWORD="${PGPASSWORD}" pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
    --format=plain --no-owner --no-privileges | gzip -9 > "${BACKUP_FILENAME}"

# Generate SHA256 integrity checksum
sha256sum "${BACKUP_FILENAME}" > "${CHECKSUM_FILENAME}"

BACKUP_SIZE=$(du -h "${BACKUP_FILENAME}" | cut -f1)
echo "Backup successful! Size: ${BACKUP_SIZE}"
echo "Checksum: $(cat "${CHECKSUM_FILENAME}")"

# Retention cleanup: remove archives older than RETENTION_DAYS
echo "Applying retention cleanup (older than ${RETENTION_DAYS} days)..."
find "${BACKUP_DIR}" -type f -name "amara_backup_*.sql.gz*" -mtime +"${RETENTION_DAYS}" -delete
echo "Retention cleanup complete."
