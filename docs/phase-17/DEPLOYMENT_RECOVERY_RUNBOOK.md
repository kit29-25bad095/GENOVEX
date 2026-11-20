# GENOVEX — Deployment Recovery and Rollback Runbook

## 1. Purpose and Incident Severity Levels

This runbook defines operational recovery procedures for unexpected deployment failures, system degradation, container crashes, or database anomalies in the GENOVEX healthcare platform.

### Severity Classification:
- **P1 — Critical Emergency:** Complete outage, API returning 5xx across multiple endpoints, database unreachable, or potential data corruption. Target Recovery Time Objective (RTO) < 15 minutes.
- **P2 — Major Degradation:** Elevated error rates (>5%), AI provider failure (operating on deterministic fallback), or single AZ outage. RTO < 60 minutes.
- **P3 — Minor Issue:** Non-critical UI glitch, background backup delay, non-blocking administrative reporting error. RTO < 4 hours.

---

## 2. Immediate Rollback Procedures (Application Layer)

### 2.1 Automated Rollback via ECS / Kubernetes
If a deployment fails readiness checks during rollout:
```bash
# 1. Inspect recent deployment revision in AWS ECS
aws ecs describe-services \
  --cluster genovex-production-cluster \
  --services genovex-backend-service \
  --region me-central-1

# 2. Revert to previous stable Task Definition revision
aws ecs update-service \
  --cluster genovex-production-cluster \
  --services genovex-backend-service \
  --task-definition genovex-backend-task:PREVIOUS_REVISION_NUMBER \
  --force-new-deployment \
  --region me-central-1

# 3. Repeat for frontend service if frontend release was involved
aws ecs update-service \
  --cluster genovex-production-cluster \
  --services genovex-frontend-service \
  --task-definition genovex-frontend-task:PREVIOUS_REVISION_NUMBER \
  --force-new-deployment \
  --region me-central-1
```

### 2.2 GitHub Actions Manual Rollback Trigger
1. Navigate to GitHub Actions -> `GENOVEX CI/CD Deployment Pipeline`.
2. Select `Run workflow`.
3. Enter the previous stable semantic tag (e.g. `v1.0.0-previous`) as the target ref.
4. Approve the production deployment gate.

---

## 3. Database Recovery Runbook

### 3.1 Scenario A: SQLite Database Corruption or WAL Sync Failure
If SQLite reports `database disk image is malformed` or integrity checks fail:

```bash
# Step 1: Temporarily route users to Maintenance Mode page
aws elbv2 modify-rule \
  --rule-arn <ALB_RULE_ARN> \
  --actions Type=fixed-response,FixedResponseConfig="{StatusCode=503,ContentType=text/html,MessageBody='<html><body><h1>GENOVEX Maintenance</h1><p>Scheduled maintenance in progress. Please check back shortly.</p></body></html>'}"

# Step 2: Stop backend tasks to release file locks
aws ecs update-service \
  --cluster genovex-production-cluster \
  --services genovex-backend-service \
  --desired-count 0 \
  --region me-central-1

# Step 3: Identify the latest verified backup from S3
aws s3 ls s3://genovex-prod-backups-me-central-1/ --region me-central-1 | sort | tail -n 5

# Step 4: Download and verify checksum
aws s3 cp s3://genovex-prod-backups-me-central-1/genovex_backup_YYYYMMDD_HHMMSS.db /app/data/genovex.db.restored
aws s3 cp s3://genovex-prod-backups-me-central-1/genovex_backup_YYYYMMDD_HHMMSS.db.sha256 /app/data/

# Verify SHA-256
sha256sum -c genovex_backup_YYYYMMDD_HHMMSS.db.sha256

# Verify SQLite integrity
sqlite3 /app/data/genovex.db.restored "PRAGMA integrity_check;"
# Output MUST be: ok

# Step 5: Replace database file safely
mv /app/data/genovex.db /app/data/genovex.db.corrupted.$(date +%s)
mv /app/data/genovex.db.restored /app/data/genovex.db
rm -f /app/data/genovex.db-wal /app/data/genovex.db-shm

# Step 6: Restart backend service and verify readiness
aws ecs update-service \
  --cluster genovex-production-cluster \
  --services genovex-backend-service \
  --desired-count 2 \
  --region me-central-1

curl -f https://genovex.ae/health/ready
```

### 3.2 Scenario B: Failed Schema Migration (Alembic Downgrade)
If an Alembic database migration fails midway:
```bash
# 1. Connect to administrative container shell
# 2. Check current migration revision
alembic current

# 3. Downgrade to prior stable revision
alembic downgrade -1

# 4. Verify table schema and constraints
python -c "from app.core.database import engine; print(engine.table_names())"
```

---

## 4. Emergency Static Maintenance Mode

In the event of an extended investigation or data recovery window, the edge CDN (Cloudflare) or Application Load Balancer can be toggled to serve a branded, bilingual maintenance notice:

```html
<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
  <meta charset="utf-8">
  <title>GENOVEX — System Maintenance</title>
  <style>
    body { font-family: system-ui, -apple-system, sans-serif; text-align: center; padding: 4rem 1rem; color: #1e293b; }
    h1 { font-size: 2rem; color: #0f172a; }
    p { font-size: 1.1rem; color: #475569; max-width: 600px; margin: 1rem auto; line-height: 1.6; }
    .ar { direction: rtl; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin-top: 2rem; }
  </style>
</head>
<body>
  <h1>GENOVEX — Scheduled Maintenance</h1>
  <p>Our clinical platform is undergoing routine maintenance to maintain the highest standards of medical data security. Assessment services will resume shortly.</p>
  <div class="ar">
    <h1>جينوفيكس — صيانة مجدولة للنظام</h1>
    <p>تخضع منصتنا السريرية حالياً لصيانة دورية لضمان أعلى معايير أمان البيانات الطبية. ستستأنف خدمات التقييم الطبي قريباً.</p>
  </div>
</body>
</html>
```

---

## 5. Post-Incident Review (PIR) Protocol

Following any P1 or P2 incident recovery:
1. **Preserve Logs:** Export all CloudWatch / Datadog logs covering the window `T-30min` to `T+30min`.
2. **Timeline Construction:** Document exact timestamps of alerts, triage actions, root cause identification, and resolution.
3. **Clinical Review:** The Medical Director must confirm whether any ongoing assessments were dropped or submitted with partial responses. Affected patients must receive notification with correlation ID references.
4. **Action Items:** File corrective Jira tickets within 24 hours to prevent reoccurrence.
