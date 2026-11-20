# GENOVEX Phase 17 Deployment & Launch Readiness Audit

## 1. Executive Summary

This pre-implementation deployment audit establishes the technical baseline, deployment gaps, hosting requirements, and launch readiness roadmap for the **GENOVEX** male reproductive health risk identification and clinical navigation platform.

### Phase Status & Architectural Preconditions
- **Phases 1–9:** Implemented and operational (core medical content, 11-domain adaptive questionnaire engine, deterministic clinical rule engine, assessment report compiler, AI safety guardrails).
- **Phase 10:** Clinician Decision Support Portal endpoints and schemas preserved and operational.
- **Phase 18:** Maintenance, Monitoring, Reliability & Future Development Infrastructure implemented and audited (`PHASE_18_FINAL_VERIFICATION_REPORT.md` confirmed **APPROVED WITH MINOR LIMITATIONS**).
- **Phases 11–16:** Pending subsequent phases (Admin Dashboard, Clinical Referral, PDF Generation, Database Migration, Security Hardening, Testing Validation).

---

## 2. Current Architecture & Codebase Inspection

| Architectural Layer | Technology Stack | Configuration / Invariants |
| :--- | :--- | :--- |
| **Frontend Framework** | Next.js 14 (React 18, TypeScript 5.7, Tailwind CSS 3.4) | Bilingual English (LTR) / Arabic (RTL), App Router, Lucide icons, Context-driven state |
| **Backend Framework** | FastAPI 0.115+ (Python 3.11/3.14 compatible, ASGI) | Lifespan events, structured logging, correlation ID middleware, centralized error normalizer |
| **Database Engine** | SQLite 3 (`genovex.db`) with Write-Ahead Logging (`WAL`) | `PRAGMA journal_mode=WAL`, `synchronous=NORMAL`, `foreign_keys=ON`, online snapshot backups |
| **Clinical Decision Logic** | Pure Deterministic Rule Engine | Zero probabilistic LLM drift; rule engine decoupled from CMS and AI; frozen historical report snapshots |
| **Reliability & AI Safety**| Phase 18 `AIMonitoringService` & `MaintenanceScheduler` | 3-state circuit breaker (`CLOSED`/`OPEN`/`HALF_OPEN`), latency/cost tracking, deterministic fallbacks |
| **Existing Deployment Assets**| `vercel.json`, `api/index.py` | Vercel Serverless Function rewrite mapping `/api/v1/:path*` to `api/index.py` |

---

## 3. Deployment Gaps & Vulnerability Analysis

### Gap 1: Vercel Serverless Ephemeral Filesystem vs. SQLite Storage
- **Finding:** `vercel.json` and `api/index.py` configure Vercel Serverless Python functions referencing `sqlite:///genovex.db`.
- **Critical Risk:** Vercel serverless lambda environments have read-only or ephemeral local storage (`/tmp` only). Writes to `genovex.db` during user assessment completion or admin CMS updates are discarded upon lambda container termination or cold recycling.
- **Requirement:** Phase 17 must provide containerized Docker deployment options and PostgreSQL transition readiness while maintaining SQLite compatibility for single-instance, staging, or serverless preview testing.

### Gap 2: Missing Containerization Infrastructure (Docker / Compose)
- **Finding:** No `Dockerfile` exists for frontend, backend, or full-stack production containers.
- **Risk:** Environment parity drift between developer workstations, staging runners, and production cloud infrastructure.
- **Requirement:** Provide multi-stage, hardened, non-root `Dockerfile` configurations for FastAPI backend, Next.js frontend, and a unified `docker-compose.yml` for local orchestration, integration testing, and single-host deployment.

### Gap 3: Missing Environment Configuration Separation
- **Finding:** The application currently relies on fallback default values in `Settings` (`backend/app/core/config.py`). There are no `.env.example`, `.env.development`, `.env.staging`, or `.env.production` templates.
- **Risk:** Developers or deployment operators may inadvertently run production with default development secrets (`"genovex-secure-secret-key-uae-2026"`), which triggers immediate security rejection in production mode.
- **Requirement:** Establish formalized `.env.example` templates with explicit environment-specific variables, strict validation rules, and zero committed credentials.

### Gap 4: Missing Automated CI/CD Pipeline
- **Finding:** No GitHub Actions workflows exist in `.github/workflows/`.
- **Risk:** Unverified code changes can be pushed directly to production without automated regression testing, security scanning, or build verification.
- **Requirement:** Implement a GitHub Actions workflow incorporating linting, static analysis, unit/integration testing, container build validation, staging deployment, and manual approval gates for production.

### Gap 5: Missing Production ASGI Process Supervision
- **Finding:** Uvicorn is invoked in development mode. No production ASGI supervisor (Gunicorn with Uvicorn worker class or container orchestrator process) is configured.
- **Requirement:** Configure Gunicorn with `uvicorn.workers.UvicornWorker`, process worker sizing (`(2 * CPU) + 1`), graceful shutdown signals (`SIGTERM`), and timeout handling.

### Gap 6: Domain, TLS & Security Headers Hardening
- **Finding:** Security response headers (Content-Security-Policy, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy) are not enforced at the application middleware level.
- **Requirement:** Implement an automated security headers middleware in FastAPI and Next.js configuration to enforce OWASP/HIPAA/UAE health security standards.

---

## 4. Hosting Requirements & Topologies

### 4.1 UAE Healthcare Sovereign Cloud Requirements
Under UAE Federal Decree-Law No. 45 of 2021 regarding Personal Data Protection and local health data residency standards (Department of Health Abu Dhabi / Dubai Health Authority):
1. **Data Residency:** All clinical assessment answers, reports, and audit logs must remain hosted within the UAE sovereign borders.
2. **Approved Cloud Regions:**
   - **AWS Middle East (UAE) — `me-central-1`** (Dubai)
   - **Microsoft Azure UAE North** (Dubai) / **UAE Central** (Abu Dhabi)
   - **Oracle Cloud Infrastructure (OCI) UAE East** (Dubai) / **UAE Central** (Abu Dhabi)
   - **Local Tier III/IV Colocated Hosting** (e.g., e& enterprise, Moro Hub, Khazna)

### 4.2 Recommended Hosting Architecture

```
                                  [ Users (UAE Ingress) ]
                                            │
                                 HTTPS (TLS 1.3 / Port 443)
                                            │
                                            ▼
                       +-----------------------------------------+
                       |      Cloudflare / Cloud Ingress WAF      |
                       |  - DDoS Mitigation & Rate Limiting      |
                       |  - TLS Termination & Edge Security Hdr  |
                       +-----------------------------------------+
                                            │
                     ┌──────────────────────┴──────────────────────┐
                     │                                             │
                     ▼ (Static & SSR Pages)                        ▼ (API & Diagnostics: /api/*)
+------------------------------------------+    +------------------------------------------+
|          Frontend Web Service            |    |           Backend API Service            |
|  Next.js 14 (Node.js 20 Alpine Container)|    |  FastAPI (Python 3.11 Container)         |
|  - Standalone output build optimization  |    |  - Gunicorn + Uvicorn Workers            |
|  - English / Arabic RTL UI               |    |  - Structured JSON Logging               |
|  - Zero client-side clinical secrets     |    |  - X-Correlation-ID Request Tracing      |
+------------------------------------------+    +------------------------------------------+
                                                                   │
                                                                   ▼
                                                +------------------------------------------+
                                                |            Database Storage              |
                                                |  - Staging / Single-Node: SQLite (WAL)   |
                                                |  - Production RDS: PostgreSQL 16 (HA)    |
                                                |  - Online Automated Snapshots            |
                                                +------------------------------------------+
```

---

## 5. Database Deployment & Migration Considerations

### Current vs. Future Topology
1. **SQLite with WAL Mode (Current Baseline):**
   - Ideal for: Local development, disposable CI/CD runners, and single-instance container deployments.
   - Preserves: Low latency, zero-network connection overhead, atomic point-in-time `sqlite3.backup` snapshots.
   - Limitation: Multi-container replica scaling will cause database write concurrency conflicts unless running on single-node volumes.
2. **PostgreSQL Transition Readiness (Phase 14 Target):**
   - All SQLAlchemy declarative models in `backend/app/models/` adhere strictly to standard SQL types (`Integer`, `String`, `Boolean`, `DateTime`, `JSON`, `Enum`) compatible with PostgreSQL 15/16.
   - Alembic baseline migrations in `backend/alembic/` already include verified PostgreSQL dialect generation (`backend/tests/test_alembic_baseline.py::test_alembic_postgresql_dialect_compatibility PASSED`).

---

## 6. Security & Launch Safety Invariants

1. **Non-Diagnostic Constraint:** The platform must never present definitive medical diagnoses or prescribe therapies.
2. **Deterministic Triage Safety Circuit:** Tier 4 acute scrotal pain (6-hour surgical emergency) and painless testicular lumps (urgent urological evaluation) must evaluate deterministically without AI interference.
3. **No Patient Exposure during Staging:** Staging deployments must strictly run with simulated synthetic assessments. Staging must never connect to live production patient databases or send real clinical notifications.
4. **Zero Committed Secrets:** All secrets, keys, and tokens must be injected via runtime environment variables or secure cloud secret managers (AWS Secrets Manager, Azure Key Vault, HashiCorp Vault).

---

## 7. Proposed Phase 17 Implementation Plan

1. **Environment Configuration Suite:** `.env.example`, `.env.staging.example`, `.env.production.example`.
2. **Containerization Infrastructure:**
   - Multi-stage, security-hardened `backend/Dockerfile` (non-root user, slim Python).
   - Multi-stage, standalone-optimized `frontend/Dockerfile` (Node.js 20 Alpine).
   - Production-ready `docker-compose.yml` for unified local/staging deployment.
3. **Production Backend Runner:** `backend/gunicorn_conf.py` with dynamic worker allocation, graceful shutdown, and trusted proxy forwarding.
4. **Security Headers Middleware:** Enhanced CORS, HSTS, and CSP enforcement in `backend/app/core/config.py` and `backend/main.py`.
5. **CI/CD Pipeline Definition:** `.github/workflows/deploy.yml` incorporating linting, testing, container builds, staging smoke tests, and manual production deployment gates.
6. **Deployment & Disaster Recovery Documentation Suite in `docs/phase-17/`:**
   - `HOSTING_ARCHITECTURE.md`
   - `ENVIRONMENT_SEPARATION.md`
   - `FRONTEND_DEPLOYMENT.md`
   - `BACKEND_DEPLOYMENT.md`
   - `DATABASE_DEPLOYMENT.md`
   - `DOMAIN_AND_HTTPS.md`
   - `CICD_PIPELINE.md`
   - `MONITORING_AND_LOGGING_INTEGRATION.md`
   - `DEPLOYMENT_RECOVERY_RUNBOOK.md`
   - `PRODUCTION_LAUNCH_CHECKLIST.md`
   - `PHASE_17_IMPLEMENTATION_REPORT.md`
