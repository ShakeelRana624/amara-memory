# AMARA Backup, Restoration & Disaster Recovery Runbook

This runbook outlines the operational protocols for scheduled backups, data integrity verification, point-in-time recovery, and disaster restoration.

---

## 1. Backup Strategy

| Backup Type | Frequency | Retention | Storage Location | Encryption |
| :--- | :--- | :--- | :--- | :--- |
| **Continuous WAL** | Real-time | 7 days | Cloud Object Storage (S3 / GCS) | AES-256 (KMS-managed) |
| **Full Database Snapshot** | Daily at 02:00 UTC | 30 days | Geo-redundant Object Storage | Gzip + AES-256 |
| **Weekly Cold Archive** | Weekly (Sunday) | 365 days | Glacier / Deep Cold Archive | Gzip + GPG Envelope |

---

## 2. Automated Snapshot Execution

Backups are executed via the hardened container utility script `deploy/scripts/backup-database.sh`:

```bash
# Manual trigger or cronjob
./deploy/scripts/backup-database.sh
```

### Operations performed:
1. Streams PostgreSQL dump via `pg_dump` with `--no-owner --no-privileges`.
2. Compresses the stream via `gzip -9`.
3. Computes a cryptographic SHA256 checksum stored in a companion `.sha256` manifest.
4. Enforces the 30-day retention policy by pruning snapshots past the retention window.

---

## 3. Disaster Recovery Restoration Procedure

In the event of database failure or corrupted state, restore from verified snapshots:

```bash
# Syntax: ./deploy/scripts/restore-database.sh <path_to_snapshot.sql.gz>
./deploy/scripts/restore-database.sh /var/backups/amara/amara_backup_amara_prod_20261113_020000Z.sql.gz
```

### Restoration Safety Steps:
1. **Pre-flight Integrity Check**: The script calculates `sha256sum` and verifies it against the snapshot manifest.
2. **Operator Confirmation**: Prompts for interactive confirmation `RESTORE-CONFIRM`.
3. **Stream Decompression**: Streams SQL instructions directly into the target database.
4. **Post-Restore Schema Synchronization**: Runs `amara migrate --direction up` to guarantee all Alembic schema revisions match the container binary.

---

## 4. Recovery Objectives (RTO & RPO)

- **Recovery Point Objective (RPO)**: $< 5\text{ minutes}$ (guaranteed via continuous WAL archiving).
- **Recovery Time Objective (RTO)**: $< 15\text{ minutes}$ for complete cluster restoration from cold backup.

