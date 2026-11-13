#!/usr/bin/env bash
# Disaster Recovery Database Restoration Script for AMARA
# Validates integrity checksum before restoring into target PostgreSQL database.

set -eo pipefail

if [ -z "$1" ]; then
    echo "Usage: $0 <path_to_backup.sql.gz>"
    echo "Example: $0 /var/backups/amara/amara_backup_amara_prod_20261113_120000Z.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"
CHECKSUM_FILE="${BACKUP_FILE}.sha256"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "ERROR: Backup file ${BACKUP_FILE} not found."
    exit 1
fi

echo "=== AMARA Disaster Recovery Database Restore ==="
echo "Source archive: ${BACKUP_FILE}"

# Validate checksum if present
if [ -f "${CHECKSUM_FILE}" ]; then
    echo "Verifying SHA256 integrity checksum..."
    sha256sum -c "${CHECKSUM_FILE}"
    echo "Checksum verified successfully."
else
    echo "WARNING: Checksum file not found. Proceeding without checksum verification."
fi

DB_HOST="${PGHOST:-postgres}"
DB_PORT="${PGPORT:-5432}"
DB_USER="${PGUSER:-amara}"
DB_NAME="${PGDATABASE:-amara_prod}"

echo "Restoring into target: ${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
read -p "Are you sure you want to overwrite '${DB_NAME}'? (type 'RESTORE-CONFIRM' to proceed): " CONFIRM
if [ "${CONFIRM}" != "RESTORE-CONFIRM" ]; then
    echo "Restore aborted by operator."
    exit 0
fi

echo "Decompressing and streaming restore into PostgreSQL..."
gunzip -c "${BACKUP_FILE}" | PGPASSWORD="${PGPASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}"

echo "Database restore completed. Running post-restore migrations..."
amara migrate --direction up
echo "AMARA restoration and migration complete."
