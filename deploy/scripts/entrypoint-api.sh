#!/usr/bin/env bash
set -eo pipefail

echo "=========================================================="
echo "AMARA REST API Container Initializing"
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Environment: ${AMARA_ENV:-production}"
echo "Storage Backend: ${AMARA_STORAGE_BACKEND:-postgres}"
echo "=========================================================="

if [ "${AMARA_STORAGE_BACKEND}" = "postgres" ]; then
    echo "Checking PostgreSQL connection and applying schema migrations..."
    
    # Wait for PostgreSQL with timeout
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
            echo "ERROR: PostgreSQL database is unreachable after ${MAX_RETRIES} attempts. Exiting."
            exit 1
        fi
        echo "Waiting for database to accept connections ($COUNT/$MAX_RETRIES)..."
        sleep 2
    done

    echo "Database reachable. Running Alembic schema migrations..."
    amara migrate --direction up
    echo "Schema migrations successfully applied."
fi

echo "Launching AMARA process: amara $*"
exec amara "$@"
