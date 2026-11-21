# GENOVEX Production Rollback and Disaster Recovery Specification

**Project:** GENOVEX Clinical Health & Genetic Risk Assessment Platform  
**Target Region:** AWS Middle East (UAE) — `me-central-1` (Dubai)  
**Recovery Targets:** RPO <= 5 minutes | RTO <= 30 minutes  

---

## 1. Rollback Triggers & Criteria

An immediate, controlled rollback must be triggered if any of the following conditions occur during deployment or within the initial 4-hour monitoring window:
1. **API Error Spike:** HTTP 5xx responses on `/api/v1/*` exceed 1% over a 5-minute sustained window.
2. **Database Migration Failure:** Alembic schema upgrade fails or table row counts diverge from source baseline (520 records across 18 tables).
3. **Clinical Governance Failure:** Any endpoint serves unapproved clinical recommendations, violates withholding rules, or fails deterministic scoring checks.
4. **Proxy Disconnection:** Frontend requests on `genovex.ae` fail to reach `api.genovex.ae` due to DNS propagation or TLS handshake failures exceeding 15 minutes.

---

## 2. Immediate Rollback Procedures

### 2.1 Frontend Rollback (Vercel)
Vercel maintains atomic, immutable deployment artifacts:
1. In the Vercel Dashboard, select **Deployments**.
2. Locate the prior known-good deployment.
3. Click the three dots menu and select **Instant Rollback**.
4. Traffic cutover occurs globally across edge locations within seconds.

### 2.2 Backend Container Rollback (AWS ECS)
```bash
# Update ECS Service to use previous task definition revision
aws ecs update-service \
    --region me-central-1 \
    --cluster genovex-prod-cluster \
    --service genovex-backend-service \
    --task-definition genovex-backend:[PREVIOUS_REVISION] \
    --force-new-deployment
```

### 2.3 Database Rollback (RDS PostgreSQL)
If database schema corruption occurs during migration:
1. **Automated Point-in-Time Recovery (PITR):**
   ```bash
   aws rds restore-db-instance-to-point-in-time \
       --region me-central-1 \
       --source-db-instance-identifier genovex-prod-db \
       --target-db-instance-identifier genovex-prod-db-restored \
       --restore-time [TIMESTAMP_BEFORE_MIGRATION]
   ```
2. **Authoritative Source Reversion:** Revert to the pre-migration baseline SQLite snapshot (`backups/genovex_pre_phase17_migration_20261121_133125.db`).

### 2.4 DNS Failback
If domain cutover causes traffic disruption:
- Revert DNS `A` / `CNAME` records at the domain registrar to point back to the staging or holding page.
- Note that DNS TTL must be kept low (300 seconds / 5 minutes) during maintenance windows to accelerate propagation.

---

## 3. Disaster Recovery (DR) Architecture

### 3.1 High Availability (Multi-AZ)
- The production RDS instance operates in Multi-AZ configuration across `me-central-1a` and `me-central-1b`. Synchronous replication ensures automatic failover within 60–120 seconds if an AZ experiences an outage, with zero data loss.
- ECS Fargate tasks are distributed equally across both Availability Zones behind the ALB.

### 3.2 Automated Backup Schedule & Retention
- **Automated RDS Snapshots:** Captured daily, retained for 35 days, encrypted with AWS KMS CMK.
- **Transaction Logs:** Archived continuously to Amazon S3 in `me-central-1`, enabling point-in-time recovery down to the second.
