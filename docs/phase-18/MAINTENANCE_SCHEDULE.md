# GENOVEX Maintenance Schedule & Operational Cadence

## 1. Automated Background Cadence

The GENOVEX background maintenance scheduler (`MaintenanceScheduler`) runs continuously within the FastAPI application lifecycle:

| Task | Frequency | Automated Mechanism | Success Verification |
| :--- | :--- | :--- | :--- |
| **Online Database Backup** | Every 360 min (6 hrs) | `sqlite3.backup` API | `PRAGMA integrity_check` == "ok" & SHA-256 written |
| **Backup Pruning** | Post-backup execution | Keep latest 10 snapshots | Retained count <= `BACKUP_RETENTION_COUNT` |
| **Clinical Asset Audit** | Every 360 min (6 hrs) | Staleness evaluation against 365-day rule | Zero unreviewed published rules/conditions |
| **AI Cooldown Evaluation** | Continuous (on request) | Circuit breaker cooldown timers | Graceful `HALF_OPEN` trial probe |

---

## 2. Weekly Operational Cadence (DevOps & Engineering)

1. **Storage Consumption Review:**
   - Review disk usage trend across database, backups, and static assets.
   - Confirm backup directory size remains bounded.
2. **AI Telemetry & Cost Analysis:**
   - Inspect average response latency, token consumption, and failure rates via `GET /api/v1/admin/maintenance/ai-telemetry`.
   - Adjust rate limits or model tiers if costs or latency spike.
3. **Log Sanitization Verification:**
   - Audit sample log streams to confirm no sensitive PII, questionnaire answers, or passwords bypass redacting filters.

---

## 3. Monthly Operational Cadence (Clinical & Regulatory)

1. **Review Audit Reconciliation:**
   - Review all conditions and rules nearing the 365-day review limit.
   - Assign pending reviews to accredited medical reviewers.
2. **Disaster Recovery Simulation:**
   - In a staging sandbox, perform a test restore from a recent production backup snapshot.
   - Verify all historical assessment reports and cryptographic checksums match.
3. **Guideline Alignment Check:**
   - Compare clinical rules against recent bulletins from AUA, EAU, and UAE health authorities (DHA, DOH, MoHAP).

---

## 4. Annual Regulatory Re-Certification

1. **Annual Security & Penetration Testing:**
   - Conduct third-party vulnerability scanning and penetration testing.
2. **UAE Health Data Compliance Audit:**
   - Audit database encryption at rest, access logs, and patient consent workflows against UAE Federal Decree-Law No. 45.
3. **Clinical Governance Sign-Off:**
   - Formal sign-off by the Chief Medical Officer on all published questionnaire domains, scoring rules, and educational articles.
