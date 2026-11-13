# AMARA Deployment Rollback & Incident Response Runbook

This runbook defines the emergency rollback protocols for service regressions, corrupted schema migrations, or infrastructure failures.

---

## 1. Application Container Rollback

If a newly deployed release exhibits elevated error rates, memory leaks, or unhandled exceptions:

### Zero-Downtime Container Rollback
```bash
# 1. Identify previous stable image tag
STABLE_TAG="v0.1.0-release"

# 2. Update service image in Kubernetes / Docker Swarm
kubectl set image deployment/amara-api api=ghcr.io/amara-ai/api:${STABLE_TAG}
kubectl rollout status deployment/amara-api

# 3. For Docker Compose deployments:
export AMARA_IMAGE_TAG=${STABLE_TAG}
docker compose up -d --no-deps api worker
```

---

## 2. Database Migration Rollback

If an Alembic migration fails or introduces performance bottlenecks:

```bash
# 1. Inspect current database revision
amara migrate --direction up --revision current

# 2. Rollback to preceding schema revision
# Example: downgrade one revision
amara migrate --direction down --revision -1

# 3. Or rollback to a specific known stable revision ID
amara migrate --direction down --revision b8a49c12df7e
```

> **Warning**: Ensure the application tier is rolled back *before* running destructive schema downgrades to avoid breaking running queries.

---

## 3. High-Load Shedding & Circuit Breaking

When the cluster encounters unexpected traffic spikes:
1. **Rate Limiter Throttling**: Lower ingress rate limits in `Caddyfile` or `nginx.conf` (e.g., from 100 r/s to 50 r/s).
2. **Worker Interval Backoff**: Increase `AMARA_WORKER_INTERVAL` from 60s to 300s to free database connections for real-time client API requests.
3. **Connection Pool Tuning**: Verify `AMARA_DB_POOL_SIZE` and `AMARA_DB_MAX_OVERFLOW` do not exceed PostgreSQL `max_connections`.
