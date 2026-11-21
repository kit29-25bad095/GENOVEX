# GENOVEX — PHASE 17: PRODUCTION ROLLBACK & RECOVERY PLAN
## Incident Response Runbooks, Blue/Green Switching & Disaster Recovery Protocols

### 1. Purpose & Incident Triggers
This Rollback and Recovery Plan establishes the technical procedures for immediately rolling back a failed deployment, restoring database integrity, or mitigating critical production vulnerabilities without data loss.

#### Rollback Triggers:
1. **Critical Health Check Failure:** Backend `/health/live` or `/health/ready` probe fails continuously for > 2 minutes post-deployment.
2. **Elevated API Error Rate:** HTTP 5xx error rate exceeds 1% of total traffic over a 5-minute window.
3. **Clinical Governance Failure:** Alteration or regression of deterministic clinical rule outcomes.
4. **Security Vulnerability Exposure:** Active exploitation of authentication, authorization, or unintended data exposure.
5. **Database Migration Failure:** Incomplete or corrupted database migration during deployment.

---

### 2. Rollback Decision Hierarchy & Roles

```
[ Incident Detected (Monitoring Alarm / Sentry / On-Call) ]
                        │
                        ▼
            [ Incident Commander (IC) ]
     (Assesses Severity & Authorizes Rollback)
                        │
         ┌──────────────┴──────────────┐
         ▼                             ▼
[ Frontend Rollback ]         [ Backend / Database Rollback ]
(Executed via Vercel)         (Executed via AWS CloudFormation / ECS)
```

---

### 3. Frontend Rollback Procedures (Vercel)

Vercel provides instant atomic rollback across its global edge network.

#### Instant Web Dashboard Rollback:
1. Navigate to the **GENOVEX** project dashboard on Vercel:
   `https://vercel.com/a4789257-6531s-projects/genovex`
2. Click on the **Deployments** tab.
3. Locate the previous verified stable production deployment (e.g., Commit `5b1703e`).
4. Click the three dots menu (`...`) on that deployment row and select **Instant Rollback**.
5. Confirm the action. Traffic is immediately redirected to the prior immutable build within < 10 seconds.

#### CLI Rollback:
```bash
# Rollback production domain to specific verified deployment URL
npx vercel rollback <deployment-id-or-url> --token=$VERCEL_TOKEN
```

---

### 4. Backend Rollback Procedures (AWS ECS Fargate / Container Cluster)

#### Automated Blue/Green Deployment Rollback:
1. In the AWS ECS Console (region `me-central-1` Dubai), locate the `genovex-backend-service`.
2. If CodeDeploy deployment was initiated, click **Stop and Roll Back Deployment**.
3. AWS CodeDeploy immediately routes 100% of ALB target traffic back to the Original (Blue) task set.
4. Wait for healthy task confirmation:
   ```bash
   aws ecs describe-services \
     --cluster genovex-cluster-prod \
     --services genovex-backend-service \
     --region me-central-1
   ```

#### Manual Task Definition Rollback:
If manual task definition revision was deployed:
```bash
# Update service to point to previous task definition revision (e.g., revision 12)
aws ecs update-service \
  --cluster genovex-cluster-prod \
  --services genovex-backend-service \
  --task-definition genovex-backend:12 \
  --force-new-deployment \
  --region me-central-1
```

---

### 5. Database Rollback & Restoration Procedures

#### Scenario A: Alembic Migration Rollback (Non-Destructive)
If a newly applied Alembic migration introduces schema defects:
```bash
# Downgrade database schema by 1 revision
cd backend
python -m alembic downgrade -1

# Verify current revision
python -m alembic current
```

#### Scenario B: Point-in-Time Database Restoration (Amazon RDS PostgreSQL)
If data corruption occurred:
1. Open the Amazon RDS Console in `me-central-1`.
2. Select the production database instance `genovex-rds-prod`.
3. Choose **Actions** -> **Restore to point in time**.
4. Select the target time (e.g., 5 minutes before the failed deployment).
5. Specify a temporary recovery instance identifier: `genovex-rds-recovery`.
6. Once provisioned, execute data integrity verification queries:
   ```sql
   SELECT COUNT(*) FROM users;
   SELECT COUNT(*) FROM assessment_reports;
   SELECT COUNT(*) FROM audit_logs;
   ```
7. Repoint the backend database connection string in AWS Secrets Manager to the recovery instance.

#### Scenario C: SQLite Staging / Local Database Restoration
```bash
# 1. Stop backend service
# 2. Locate latest clean daily backup in ./backend/backups
python -c "
from app.services.backup_service import BackupService
from app.core.database import SessionLocal
db = SessionLocal()
BackupService.restore_backup('genovex_backup_20261121_000000.tar.gz', db)
"
```

---

### 6. Post-Rollback Review & Root Cause Analysis (RCA)

Following any production rollback event:
1. Hold a blameless post-mortem within 24 hours involving engineering, clinical governance, and operations.
2. Produce a formal RCA document detailing:
   - Root cause failure mode.
   - Time to detection (MTTD) and time to recovery (MTTR).
   - Data impact assessment (confirming zero data loss or PHI exposure).
   - Actionable preventive engineering items required before re-attempting deployment.
