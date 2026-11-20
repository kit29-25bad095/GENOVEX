# GENOVEX — Database Deployment & Migration Strategy

## 1. Current State & Production Transition

GENOVEX currently operates with an authoritative SQLite 3 database (`genovex.db`) configured with high-performance concurrency settings:
- **Write-Ahead Logging (WAL):** Enabled via `PRAGMA journal_mode=WAL;`
- **Synchronous Mode:** Set to `NORMAL` (`PRAGMA synchronous=NORMAL;`)
- **Foreign Keys:** Enforced at connection time (`PRAGMA foreign_keys=ON;`)
- **Busy Timeout:** 10,000ms to eliminate locking contention (`PRAGMA busy_timeout=10000;`)

While SQLite WAL provides rapid development and deterministic local execution, production enterprise operation in the UAE healthcare ecosystem requires a clear database lifecycle strategy spanning containerized WAL volume persistence and the upcoming Phase 14 managed PostgreSQL migration.

---

## 2. Containerized SQLite Persistence (Current Phase 17/18)

When deploying GENOVEX containers with SQLite:

### 2.1 Storage Volume Architecture
- The SQLite file and its accompanying `-wal` and `-shm` temporary files **must not** reside on ephemeral container layers.
- In Docker Compose: Mounted via named volume `genovex-data:/app/data`.
- In AWS ECS / Kubernetes: Mounted via an **AWS EBS `gp3` volume** formatted with `ext4` or an **AWS EFS** volume configured with POSIX file locking.
- **Never host SQLite on SMB / Windows CIFS network shares**, as CIFS does not properly support POSIX advisory locks required by SQLite WAL.

### 2.2 Backup Strategy
- Phase 18's automated `BackupService` executes continuous WAL-safe snapshotting via `sqlite3.Connection.backup()` to `/app/backups`.
- Snapshots are cryptographically verified using SHA-256 and pruned according to `BACKUP_RETENTION_COUNT` (default: 7 in dev, 14 in staging, 30 in production).
- An automated cron or sidecar synchronizes verified snapshots to an encrypted AWS S3 bucket in `me-central-1`.

---

## 3. Managed PostgreSQL Architecture (Target Phase 14)

In Phase 14 (Database and API Integration), GENOVEX will transition to **Amazon RDS for PostgreSQL (Engine 16.x)**.

### 3.1 RDS Production Topology
- **Region:** AWS UAE (`me-central-1` Dubai).
- **Deployment:** Multi-AZ with synchronous replication across AZs (`me-central-1a` and `me-central-1b`).
- **Instance Class:** `db.m7g.large` (2 vCPU, 8 GB RAM, Graviton3 processor).
- **Storage:** 100 GB gp3 storage with auto-scaling up to 1 TB, encrypted with AWS KMS customer-managed key.
- **Connection Pooling:** Amazon RDS Proxy / PgBouncer to manage high-frequency connection pooling and prevent connection exhaustion.
- **Automated Backups:** Daily automated snapshots with 35-day point-in-time recovery (PITR) retention.

```
┌────────────────────────────────────────────────────────┐
│                   AWS VPC (me-central-1)               │
│                                                        │
│  [ FastAPI Tasks (ECS) ]   [ FastAPI Tasks (ECS) ]     │
│             │                           │              │
│             └─────────────┬─────────────┘              │
│                           ▼                            │
│                  [ Amazon RDS Proxy ]                  │
│               - Connection Multiplexing                │
│               - Zero-Downtime Failover (<30s)          │
│                           │                            │
│            ┌──────────────┴──────────────┐             │
│            ▼                             ▼             │
│   [ Primary RDS Postgres ]   [ Standby Replica ]       │
│      (me-central-1a)             (me-central-1b)       │
│      - Multi-AZ Sync             - Automatic Failover  │
└────────────────────────────────────────────────────────┘
```

---

## 4. SQLite to PostgreSQL Migration Runbook

The schema is maintained using SQLAlchemy ORM models, making database abstraction direct and controlled:

### Step 1: Pre-Migration Schema Validation
1. Use Alembic (`alembic/`) to verify that all models in `app.models` match the target PostgreSQL schema.
2. Ensure UUID, DateTime with timezone, and JSON column types are mapped to native PostgreSQL types (`UUID`, `TIMESTAMP WITH TIME ZONE`, `JSONB`).

### Step 2: Data Extraction & Export
```bash
# 1. Place the backend into read-only maintenance mode
export MAINTENANCE_MODE=True

# 2. Perform a final clean checkpoint of the SQLite database
python -c "
import sqlite3
conn = sqlite3.connect('genovex.db')
conn.execute('PRAGMA wal_checkpoint(TRUNCATE);')
conn.close()
"

# 3. Export data using pgloader or python ETL script
pgloader sqlite:///app/data/genovex.db postgresql://genovex_user:SecretPass@rds-postgres.internal:5432/genovex_prod
```

### Step 3: Sequence & Constraint Verification
1. Reset all serial sequences in PostgreSQL to `MAX(id) + 1`.
2. Verify foreign key constraints and unique indexes:
   ```sql
   SELECT conname, contype, confrelid::regclass 
   FROM pg_constraint 
   WHERE connamespace = 'public'::regnamespace;
   ```

### Step 4: Cutover & Health Check
1. Update `DATABASE_URL` in AWS Secrets Manager:
   `postgresql://genovex_user:${DB_PASSWORD}@rds-postgres.internal:5432/genovex_prod?sslmode=verify-full`
2. Restart backend tasks.
3. Validate `/health/ready` responds with `200 OK` and `"database": "connected"`.
