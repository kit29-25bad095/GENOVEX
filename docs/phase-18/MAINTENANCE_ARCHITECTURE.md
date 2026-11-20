# GENOVEX Maintenance & Reliability Architecture

## 1. Architectural Philosophy & Healthcare Safety Principles

GENOVEX is an AI-assisted male reproductive health risk identification and clinical navigation platform designed specifically for the United Arab Emirates (UAE) healthcare ecosystem. Given the deeply sensitive, cultural, and clinical nuances of male fertility and reproductive well-being, the system's operational architecture is governed by strict reliability and safety axioms:

1. **Deterministic Primacy:**
   - Diagnostic guidance, risk tier stratifications, and clinical referrals are strictly compiled by deterministic clinical rules based on validated guidelines (AUA, EAU, WHO, DHA, DOH, MoHAP).
   - Machine Learning / Large Language Model systems provide supportive multilingual translations, conversational summaries, and readability enhancements *only*. Under no circumstances does an AI component alter, override, or invent clinical risk tiers.

2. **Fault Isolation & Graceful Degradation:**
   - Any external dependency failure (e.g., AI API timeouts, LLM rate limits) triggers an immediate circuit break into a safe, deterministic fallback mode with zero downtime or user obstruction.
   - Core questionnaire traversal and deterministic report generation operate reliably even if peripheral subsystems are unavailable.

3. **Auditable Immutability:**
   - Health assessment records, once completed, are cryptographically pinned to the exact version of the questionnaire and clinical rules that evaluated them.
   - Content changes, clinical rule modifications, and questionnaire revisions adhere to strict semantic versioning and immutable audit trails.

---

## 2. Subsystem Boundaries and Component Map

```
+-----------------------------------------------------------------------------------+
|                                 Client Layer                                      |
|    Next.js 14 Web Application (Bilingual: English & Arabic, RTL Compliant)       |
+-----------------------------------------------------------------------------------+
                                         |
                       REST API (HTTPS + X-Correlation-ID)
                                         v
+-----------------------------------------------------------------------------------+
|                            FastAPI Gateway & Middlewares                          |
|  - Request Correlation ID Middleware (X-Correlation-ID Propagation)               |
|  - Security & RBAC Middleware (NIST PBKDF2, JWT HS256, DHA/DOH Role Hierarchy)   |
|  - Centralized Error Normalizer & PII/Answer Redacting JSON Logger                |
+-----------------------------------------------------------------------------------+
       |                        |                         |                  |
       v                        v                         v                  v
+--------------+       +------------------+       +---------------+   +--------------+
| Health & Ops |       | Clinical Assets  |       | AI Reliability|   | Backup & DR  |
| - /api/health|       | - Content Engine |       | - Circuit Brk |   | - SQLite WAL |
| - Diagnostic |       | - Rule Engine    |       | - Fallback LLM|   | - Checksum   |
| - Metrics    |       | - Q-Versioning   |       | - Token/Lat Tr|   | - Pruning    |
+--------------+       +------------------+       +---------------+   +--------------+
       \                        |                         |                  /
        \                       v                         v                 /
+-----------------------------------------------------------------------------------+
|                        Async Maintenance Scheduler (Lifespan)                     |
|  - Periodic SQLite Online Snapshot Backups                                        |
|  - Automated Clinical Asset Staleness & Review Auditing (180-Day Rule)            |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                       Database Storage & Persistence                              |
|  - SQLite 3 (WAL Mode, synchronous=NORMAL, foreign_keys=ON)                      |
|  - Atomic Online Backup API via sqlite3.backup                                    |
|  - Encrypted, Checksummed Cold Snapshot Storage                                   |
+-----------------------------------------------------------------------------------+
```

---

## 3. Reliability Principles & Redundancy

### 3.1 Database Reliability (SQLite WAL Mode)
By configuring SQLite with:
- `PRAGMA journal_mode=WAL;`
- `PRAGMA synchronous=NORMAL;`
- `PRAGMA foreign_keys=ON;`
- `PRAGMA busy_timeout=5000;`

The system enables concurrent multi-threaded reads without blocking write transactions. The database connection pool utilizes an SQLite online backup procedure (`sqlite3.backup`) to perform point-in-time snapshots without locking tables or degrading API response latency.

### 3.2 AI Service Resilience (Circuit Breaker Pattern)
To ensure compliance with UAE healthcare resilience standards, the AI Service is guarded by a triple-state circuit breaker:
- **CLOSED:** Normal operation. Calls to LLM/AI services are monitored for latency and error rates.
- **OPEN:** After 5 consecutive failures or repeated timeouts (>10s), the breaker trips. Subsequent requests immediately bypass external network calls and execute pre-validated deterministic fallbacks.
- **HALF_OPEN:** After a 60-second recovery window, probe requests evaluate API availability. Successful probes close the circuit; failures reopen it immediately.

---

## 4. Security & Compliance Safeguards (UAE Healthcare Standards)

1. **PII and Reproductive Answer Redaction:**
   - The structured JSON logging engine applies regular expression filters before writing to streams or files.
   - Field names containing `password`, `token`, `secret`, `authorization`, `answers`, `symptoms`, or `responses` are automatically masked to `[REDACTED]`.
2. **Deterministic Immutability:**
   - When a patient completes an assessment, the snapshot is recorded with `questionnaire_version_id` and `rule_engine_version`. Historical assessments are never re-evaluated dynamically, guaranteeing medical reproducibility in case of clinical audit or legal inquiry.
3. **Role-Based Access Control (RBAC):**
   - High-privilege maintenance endpoints (`/api/v1/admin/health/diagnostics`, `/api/v1/admin/maintenance/*`) require `ADMIN` or `SUPERADMIN` authorization. Unauthorized callers receive standard 403 Forbidden responses.
