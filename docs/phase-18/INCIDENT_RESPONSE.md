# GENOVEX Incident Response & Clinical Safety Escalation Runbook

## 1. Severity Classification Matrix

| Severity Level | Definition | Impact | Response SLA |
| :--- | :--- | :--- | :--- |
| **P0 — Critical** | Total platform outage, database corruption, or clinical safety logic failure (e.g., Tier 4 red flags failing to trigger). | Complete service disruption or patient risk. | **< 15 minutes** |
| **P1 — High** | Core assessment evaluation degraded, database read-only/lock contention, or external AI circuit persistently tripped. | Users experience fallbacks or delays. | **< 1 hour** |
| **P2 — Medium** | Non-critical administrative endpoint failures, backup failure warning, or localized UI translation glitches. | Core assessment operational; minor administrative impact. | **< 4 hours** |
| **P3 — Low** | Minor cosmetic styling issues, documentation updates, or non-urgent metric warnings. | Negligible operational impact. | **< 24 hours** |

---

## 2. Clinical Safety Escalation Protocol

If an incident involves potential medical inaccuracies or failure of deterministic safety rules:
1. **Immediate Quarantine:**
   - If evaluation logic is suspected of corruption, clinical leads immediately toggle maintenance mode or disable new assessment submissions.
2. **Notification of Medical Director:**
   - Immediate notification to the designated UAE Clinical Reviewer and Medical Director.
3. **Forensic Report Snapshot Audit:**
   - Query `audit_logs` and `assessment_reports` within the incident window to identify all affected session tokens.
   - Cross-examine responses against deterministic guidelines.
4. **Patient Notification Runbook:**
   - If a clinical referral recommendation was erroneously omitted, affected patients are flagged for direct outreach by licensed clinicians.

---

## 3. Technical Runbook for Common Incident Scenarios

### Scenario A: Database Unresponsive / HTTP 503
1. Check process status: `ps aux | grep uvicorn` or task manager on Windows.
2. Check disk space: `df -h` or `HealthService.check_storage()`.
3. Verify SQLite lock state: Check for lingering `.db-wal` or `.db-shm` locks.
4. If corrupt, follow the [Database Disaster Recovery Guide](file:///C:/Users/Maya%20P/.gemini/antigravity/scratch/GENOVEX/docs/phase-18/DATABASE_BACKUP_RECOVERY.md).

### Scenario B: AI Circuit Breaker Stuck in OPEN State
1. Check telemetry: `GET /api/v1/admin/maintenance/ai-telemetry`.
2. Inspect upstream provider status page (OpenAI, Anthropic, Google Vertex AI).
3. If provider has recovered:
   - Call `POST /api/v1/admin/maintenance/ai-telemetry/reset` to force transition back to `CLOSED`.
   - Monitor average latency for 5 minutes.

### Scenario C: Backup Job Failure Alert
1. Inspect server logs for `backup_service` errors.
2. Verify available disk space in `backend/backups/`.
3. Trigger immediate manual backup: `POST /api/v1/admin/maintenance/backups/create`.
4. Inspect SHA-256 and integrity check output.

---

## 4. Post-Incident Review (PIR) Requirements

Within 48 hours of resolving any P0 or P1 incident, an engineering and clinical PIR document must be published:
1. Executive summary and timeline of events (UTC and GST).
2. Root cause analysis (5 Whys methodology).
3. Clinical impact assessment.
4. Remediation actions and preventative automated test additions.
