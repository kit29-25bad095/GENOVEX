# GENOVEX — Monitoring, Logging, and Backup Integration

## 1. Observability Architecture

GENOVEX incorporates a multi-tiered observability stack engineered in Phase 18 and integrated into production deployment infrastructure in Phase 17:

```
 ┌─────────────────────────────────────────────────────────────┐
 │                      GENOVEX Workloads                      │
 │                                                             │
 │   [ Next.js Frontend ]           [ FastAPI Backend ]        │
 │   - Access Logs                   - Correlation ID Tracing  │
 │   - Client Error Reporting        - Structured JSON Logs    │
 │                                   - Health Check Probes     │
 └──────────────┬──────────────────────────────┬───────────────┘
                │                              │
                ▼                              ▼
 ┌─────────────────────────────────────────────────────────────┐
 │               Collection & Ingestion Layer                  │
 │                                                             │
 │   [ AWS CloudWatch / Datadog Agent (me-central-1) ]         │
 │   - Container Log Driver (awslogs)                          │
 │   - Prometheus Scraper (/api/v1/health/detailed)            │
 │   - Metric Filters & CloudWatch Alarms                      │
 └──────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                 Alerting & Notification Engine              │
 │                                                             │
 │   [ PagerDuty / Opsgenie ]  ──▶  [ SRE On-Call Engineers ]  │
 │   [ Slack Clinical Alerts ] ──▶  [ Medical Review Board ]   │
 └─────────────────────────────────────────────────────────────┘
```

---

## 2. Health Probes & Endpoint Integration

The backend exposes four standardized health check endpoints mounted in `app/api/v1/endpoints/health.py`:

### 2.1 Liveness Probe (`GET /health/live`)
- **Consumer:** Kubernetes kubelet / AWS ECS task agent.
- **Check:** Rapid non-blocking process responsiveness check.
- **Response:** `{"status": "alive", "timestamp": "..."}` with HTTP 200.

### 2.2 Readiness Probe (`GET /health/ready`)
- **Consumer:** Application Load Balancer target group / deployment rollout gates.
- **Checks:**
  1. Database connection probe (`SELECT 1`).
  2. Core schema existence (`medical_conditions`, `questions`, `clinical_rules`).
  3. Maintenance background scheduler heartbeat.
- **Response:** `200 OK` if all operational; `503 Service Unavailable` if database or core components are disconnected.

### 2.3 Detailed Diagnostic Probe (`GET /health/detailed`)
- **Consumer:** Prometheus / CloudWatch Synthetics / Internal SRE dashboard.
- **Checks:**
  - Memory consumption (RSS in MB, CPU utilization %).
  - SQLite WAL file size and journal mode.
  - Backup integrity status (last successful backup timestamp, checksum validation).
  - AI circuit breaker state (closed, open, or half-open).

---

## 3. Structured Logging & Correlation Tracing

All backend application logs adhere to structured JSON formatting (`app/core/logging_config.py`):

```json
{
  "timestamp": "2026-11-20T17:45:12.345Z",
  "level": "INFO",
  "logger": "genovex_main",
  "message": "POST /api/v1/assessment/evaluate responded 200 in 18.42ms (IP: 10.0.1.45)",
  "correlation_id": "gnx_9f8e7d6c5b4a",
  "extra": {
    "method": "POST",
    "path": "/api/v1/assessment/evaluate",
    "status_code": 200,
    "duration_ms": 18.42,
    "client_ip": "10.0.1.45"
  }
}
```

### Privacy & Healthcare Data Sanitization Rules:
1. **Zero Patient Identifiers in Logs:** Email addresses, patient names, mobile numbers, and questionnaire answers are strictly redacted prior to log emission.
2. **Correlation ID Header:** Every HTTP response includes `X-Correlation-ID: gnx_<hex12>`. In the event of a frontend error, the user or clinician is shown this ID to enable precise log correlation without sharing medical disclosures.

---

## 4. Production Alerting Thresholds

The following CloudWatch / Datadog alarms are established for production launch readiness:

| Metric | Threshold | Evaluation Period | Severity | Action |
| :--- | :--- | :--- | :--- | :--- |
| **API Error Rate (5xx)** | > 1.0% of total requests | 3 consecutive minutes | **Critical (P1)** | Page SRE on-call via PagerDuty |
| **P95 Latency** | > 800ms on `/api/*` | 5 consecutive minutes | **High (P2)** | Slack alert to backend team |
| **Readiness Check Failure** | Target unhealthy for 2 checks | 1 minute | **Critical (P1)** | Automated ECS task restart & page |
| **AI Circuit Breaker Open** | State = `OPEN` for > 2 min | Immediate | **High (P2)** | Fallback to deterministic engine alert |
| **Database Disk Free Space** | < 20% remaining | 15 minutes | **High (P2)** | Storage volume auto-expansion trigger |
| **Backup Age** | Last backup > 25 hours old | Daily at 04:00 UTC | **High (P2)** | Backup failure notification to DevOps |

---

## 5. Automated Backup Engine & Off-Site Replication

Phase 18 introduced the automated `BackupService` (`app/services/backup_service.py`), integrated with the background `MaintenanceScheduler`:

1. **Local Snapshot:**
   - Executed automatically every 24 hours at 02:00 UAE local time (22:00 UTC) during lowest traffic.
   - Uses native `sqlite3.Connection.backup()` to create consistent point-in-time snapshots without locking read operations.
   - Generates SHA-256 integrity checksums stored alongside the backup file (`.db.sha256`).
2. **Off-Site Sovereign Replication:**
   - A secure worker task synchronizes verified snapshots from `/app/backups` to the designated encrypted AWS S3 bucket in `me-central-1` (`genovex-prod-backups-me-central-1`).
   - Transfer uses AWS KMS encryption with customer-managed keys.
3. **Retention & Pruning:**
   - The backup engine automatically retains the latest 30 snapshots in production, safely purging older archives.
