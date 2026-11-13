#!/usr/bin/env bash
set -eo pipefail

echo "=========================================================="
echo "AMARA Background Worker Container Initializing"
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Environment: ${AMARA_ENV:-production}"
echo "Storage Backend: ${AMARA_STORAGE_BACKEND:-postgres}"
echo "=========================================================="

if [ "${AMARA_STORAGE_BACKEND}" = "postgres" ]; then
    echo "Waiting for API service and database readiness..."
    MAX_RETRIES=30
    COUNT=0
    until python -c "
import asyncio, os
from amara.storage.database import DatabaseManager
async def check():
    url = os.getenv('AMARA_DATABASE_URL', 'postgresql+asyncpg://amara:amara@postgres:5432/amara_prod')
    mgr = DatabaseManager(connection_uri=url, pool_size=1)
    await mgr.initialize()
    await mgr.close()
asyncio.run(check())
" > /dev/null 2>&1; do
        COUNT=$((COUNT + 1))
        if [ "$COUNT" -gt "$MAX_RETRIES" ]; then
            echo "ERROR: PostgreSQL database unreachable for worker after ${MAX_RETRIES} attempts. Exiting."
            exit 1
        fi
        echo "Waiting for database readiness ($COUNT/$MAX_RETRIES)..."
        sleep 2
    done
fi

mkdir -p /tmp/amara
echo "Launching AMARA Worker: amara $*"
exec amara "$@"
