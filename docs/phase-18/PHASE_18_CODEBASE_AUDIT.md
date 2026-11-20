# GENOVEX — Phase 18 Codebase Audit
## Maintenance, Monitoring, Reliability & Future Development Infrastructure

**Date of Audit:** November 20, 2026  
**Auditor Roles:** Principal Software Architect, Senior Full-Stack Engineer, DevOps Engineer, Database Reliability Engineer, Application Security Engineer, Healthcare Software Maintenance Specialist  
**Target Platform:** GENOVEX (UAE Digital Male Reproductive Health Risk Identification & Clinical Navigation Platform)  
**System Status:** Functional, 23/23 tests passing, clean working tree on `main` branch.

---

## 1. Existing Technology Stack

### Backend & Core Runtime
- **Language & Runtime:** Python 3.14.6 (64-bit on Windows PowerShell execution environment).
- **Web Framework:** FastAPI `>=0.115.0` (ASGI app, lifespan context manager).
- **ASGI Server:** Uvicorn (standard extras) `>=0.30.0`.
- **ORM & Data Layer:** SQLAlchemy `>=2.0.30` (declarative Base, connection pooling, SQLite dialect with `check_same_thread=False`).
- **Data Validation & Settings:** Pydantic `>=2.9.0` (v2 `ConfigDict`, `field_validator`, `model_dump`), `pydantic-settings>=2.5.0`.
- **Database Migrations:** Alembic (current head stamped: `1646c9c659b6`).
- **Security & Cryptography:** 
  - NIST-approved `pbkdf2_sha256` password hashing via Passlib.
  - JWT tokens via `PyJWT` with `HS256` symmetric signing.
  - Role-Based Access Control (RBAC): `PATIENT`, `CLINICIAN`, `ADMIN`, `SUPERADMIN`.
  - Development authentication simulation bypass gated behind `DEBUG=True` and `ALLOW_SIMULATED_AUTH=True`.
- **Testing Framework:** Pytest `>=8.3.0` with `httpx>=0.27.0` (TestClient), AnyIO, Hypothesis.

### Frontend & Static Client Layer
- **Architecture:** Server-mounted interactive static single-page web applications and public landing pages served via FastAPI `StaticFiles` and Jinja2 templates.
- **Styling & UI Kit:** Tailwind CSS (CDN-delivered with custom brand palette `#153B55` Deep Navy, `#159A91` Vibrant Teal, `#F5F8FA` Slate Gray, `#0E273A` Midnight Dark).
- **Typography:** Google Fonts: `Manrope` (headings), `Inter` (body copy), `Noto Sans Arabic` (Arabic RTL typography).
- **Internationalization (i18n):** Client-side dynamic English (LTR) and Arabic (RTL) localization with live direction (`dir="rtl"`) and CSS layout flipping.

### Database
- **Engine:** SQLite 3 (Database file: `genovex.db`).
- **Tables:** 14 core tables with normalized schemas, foreign keys, and indexes:
  - `users`, `audit_logs`
  - `medical_categories`, `medical_references`, `medical_conditions`, `condition_contents`, `condition_references`, `content_versions`, `clinical_review_records`
  - `questionnaire_versions`, `questions`, `assessments`, `assessment_responses`
  - `clinical_rules`, `clinical_rule_versions`
  - `assessment_reports`

---

## 2. Existing Project Architecture

The GENOVEX codebase exhibits strong modular separation:

```
GENOVEX/
├── backend/
│   ├── alembic/                      # Database migration scripts & environments
│   │   ├── versions/                 # 4 migration revisions (up to 1646c9c659b6)
│   │   └── env.py                    # Metadata-aware migration environment
│   ├── app/
│   │   ├── api/v1/endpoints/         # Modular REST API endpoints
│   │   │   ├── auth.py               # Authentication, token generation, user audit
│   │   │   ├── admin_medical_content.py # Medical Content CMS endpoints
│   │   │   ├── public_health_library.py # Public educational endpoints
│   │   │   ├── questionnaire.py      # Patient questionnaire runtime endpoints
│   │   │   ├── admin_questionnaire.py# Questionnaire authoring & approval endpoints
│   │   │   ├── assessment_evaluation.py # Deterministic clinical evaluation & report endpoints
│   │   │   └── admin_clinical_rules.py  # Clinical rule registry & review endpoints
│   │   ├── core/
│   │   │   ├── config.py             # Pydantic BaseSettings configuration
│   │   │   ├── database.py           # Engine & SessionLocal factory
│   │   │   ├── security.py           # Passlib hashing, JWT tokens, RBAC dependencies
│   │   │   ├── seed_data.py          # Seeds categories, references, conditions, users
│   │   │   ├── seed_questionnaire.py # Seeds 19 clinical questions across 11 domains
│   │   │   └── seed_clinical_rules.py# Seeds 14 deterministic clinical rules
│   │   ├── models/                   # SQLAlchemy ORM model declarations
│   │   │   ├── medical_content.py    # 20-field medical conditions & versions
│   │   │   ├── questionnaire.py      # Questionnaire versions, questions, responses
│   │   │   ├── clinical_rules.py     # Deterministic rules & historical version records
│   │   │   └── assessment_report.py  # Frozen report snapshots with citations
│   │   ├── schemas/                  # Pydantic v2 schemas
│   │   │   ├── auth.py
│   │   │   ├── medical_content.py
│   │   │   ├── questionnaire.py
│   │   │   ├── clinical_rules.py
│   │   │   └── assessment_report.py
│   │   ├── services/                 # Business logic decoupled from transport
│   │   │   ├── medical_content_service.py
│   │   │   ├── questionnaire_service.py
│   │   │   ├── clinical_rule_engine.py
│   │   │   └── clinical_rule_management_service.py
│   │   └── static/                   # Interactive client web interfaces
│   │       ├── adaptive_questionnaire.html
│   │       ├── admin_clinical_rules.html
│   │       ├── admin_medical_content.html
│   │       └── public_health_library.html
│   ├── tests/                        # 23 automated pytest test cases
│   │   ├── test_medical_content.py
│   │   ├── test_adaptive_questionnaire.py
│   │   └── test_clinical_rule_engine.py
│   └── main.py                       # FastAPI application entry point
├── docs/                             # Architectural blueprints and audit documents
├── genovex.db                        # SQLite database
├── requirements.txt                  # Python dependencies
└── README.md                         # Project documentation
```

---

## 3. Existing Frontend Modules

1. **Patient Adaptive Questionnaire (`/assessment` -> `adaptive_questionnaire.html`):**
   - 11-Domain visual stepper with live progress percentage calculation.
   - Dynamic conditional question visibility (child questions hidden until parent affirmative).
   - "Unsure" and "Prefer not to answer" dedicated safe-answer buttons.
   - Pre-submission review screen displaying answers across all domains.
   - Post-submission evaluation calling the deterministic rule engine.
   - Comprehensive evidence-linked clinical report display with printable/PDF export layout.
2. **Admin Medical Content CMS (`/admin/medical-content` -> `admin_medical_content.html`):**
   - 20-field structured editor for conditions (causes, symptoms, pathophysiology, clinical steps, Arabic translations).
   - Clinical review lifecycle: Draft -> Submitted for Review -> Approved -> Published.
   - Version history and one-click rollback snapshot restoration.
   - Live audit log viewer.
3. **Public Health Library (`/health-library` -> `public_health_library.html`):**
   - Consumes published medical conditions dynamically.
   - Real-time bilingual English / Arabic toggle with RTL layout adjustment.
   - Guideline references drawer linking WHO, EAU, and AUA citations.
4. **Clinical Rule Registry (`/admin/clinical-rules` -> `admin_clinical_rules.html`):**
   - Clinical rule filtering by domain, tier, publication status, and urgency.
   - Rule editor for trigger predicates, rationales, and guideline citations.
   - Clinician review approval modal with mandatory audit verification notes.

---

## 4. Existing Backend Modules

1. **Authentication & RBAC (`app/api/v1/endpoints/auth.py`, `app/core/security.py`):**
   - Password hashing with PBKDF2-SHA256.
   - JWT bearer token issuance and validation.
   - Role enforcement (`PATIENT`, `CLINICIAN`, `ADMIN`, `SUPERADMIN`).
   - Immutable audit logging to `audit_logs` table.
2. **Medical Content Management (`app/services/medical_content_service.py`):**
   - Decoupled from clinical assessment rules.
   - Full versioning via `content_versions` table.
3. **Adaptive Questionnaire Service (`app/services/questionnaire_service.py`):**
   - 11 domains with version pinning (`assessment.questionnaire_version_id`).
   - Safe answers: `is_unsure` and `is_prefer_not_to_say` flags preserved.
4. **Deterministic Clinical Rule Engine (`app/services/clinical_rule_engine.py`):**
   - 4-Tier outcome classification (`NO_REPORTED_RISK_FACTORS`, `RISK_FACTORS_IDENTIFIED`, `CLINICAL_EVALUATION_RECOMMENDED`, `URGENT_MEDICAL_ASSESSMENT`).
   - Priority urgent safety circuit for acute pain (testicular torsion) and painless lump (neoplasm).
   - Compiles immutable `AssessmentReport` snapshots ensuring 100% historical reproducibility.
5. **Basic System Health Check (`GET /health` in `main.py`):**
   - Currently returns a hardcoded static JSON dictionary: `{"status": "online", "platform": "GENOVEX...", "version": "1.0.0"}`.
   - Does NOT perform live database ping, disk check, memory check, or dependency verification.

---

## 5. Existing Database Architecture

- **Database Engine:** SQLite 3 (`genovex.db`).
- **ORM:** SQLAlchemy 2.0 with session-per-request lifecycle via FastAPI dependency injection.
- **Migration Framework:** Alembic with 4 versions (`533c8a2b71cf`, `6bfbdbe66807`, `1646c9c659b6`).
- **Integrity Constraints:** Foreign keys with `ondelete="CASCADE"` on child records, unique indexes on keys (`rule_code`, `session_token`, `slug`, `version_tag`).
- **Backup State:** Currently relies on local static file storage. No automated backup scheduling, WAL mode enforcement, backup rotation, or disaster recovery tooling is currently implemented.

---

## 6. Existing Infrastructure

- **Operating Environment:** Windows PowerShell with Python 3.14.6 runtime.
- **Configuration:** `app/core/config.py` using `pydantic-settings` reading from system environment variables with sensible defaults.
- **Containerization / CI/CD:** No Dockerfile, docker-compose.yml, or GitHub Actions workflow currently committed in the repository.
- **Storage:** Local filesystem SQLite database file and static HTML assets.

---

## 7. Existing Maintenance Capabilities

- **Audit Logging:** Implemented in `audit_logs` table for administrative content modifications and review actions.
- **Content Versioning:** Supported for Medical Conditions (`content_versions`), Questionnaire Versions (`questionnaire_versions`), and Clinical Rules (`clinical_rule_versions`).
- **Report Freezing:** Pinned snapshots in `assessment_reports` prevent retrospective rule changes from altering historical patient outcomes.

---

## 8. Identified Maintenance & Reliability Gaps

| Module | Existing State | Gap / Vulnerability |
| :--- | :--- | :--- |
| **Health Monitoring** | Basic static `/health` endpoint returning hardcoded JSON. | No real-time database connectivity ping, no memory/disk check, no latency metrics, no degraded state detection. |
| **Logging Architecture** | Standard Python prints or uncaught stdout. | No structured JSON logging, no request correlation IDs (`X-Correlation-ID`), no log sanitization for sensitive reproductive health or auth tokens. |
| **Error Handling** | Standard FastAPI unhandled exception traces. | Internal errors could expose stack traces; no centralized exception interceptor with error codes and diagnostic correlation IDs. |
| **Database Reliability** | Single SQLite file (`genovex.db`). | No automated online backup (e.g. SQLite backup API / VACUUM INTO), no WAL (Write-Ahead Logging) optimization, no backup integrity verification or automated restoration test scripts. |
| **AI Integration Monitoring** | Phase 9 conceptual integration without operational monitoring. | No circuit breaker, timeout policy, token usage tracker, rate-limit handler, or fallback mechanism to preserve deterministic rule integrity when an AI service fails. |
| **Maintenance Scheduling** | No scheduled tasks or background workers. | No periodic database backup scheduler, no log rotation, no stale session/token cleanup, no automated clinical review reminder triggers. |
| **Incident Response** | None documented. | No standardized incident classification (P0-P3), escalation protocol, containment procedure, or patient safety triage protocol. |
| **Technical Documentation** | Generic README and blueprint artifact. | Missing dedicated Phase 18 maintenance, backup/recovery, monitoring, logging, and future development readiness guides. |

---

## 9. Technical Risks

1. **Data Loss Risk:** SQLite without automated Write-Ahead Logging (WAL) and scheduled snapshots risks corruption or lock contention under concurrent load.
2. **Information Leakage Risk:** Standard traceback logging could accidentally capture authorization headers, passwords, or patient reproductive answers.
3. **AI Contamination Risk:** In future LLM integration, unmonitored external API failures or hallucinations could disrupt assessment workflows unless isolated by strict timeout and fallback circuits.
4. **Maintenance Staleness Risk:** Clinical guidelines (EAU, AUA, WHO) update periodically; without automated review-date tracking and reminder triggers, medical content could lapse past review validity.

---

## 10. Files Likely to Require Modification or Creation

### Files to Modify
- `backend/app/core/config.py`: Add structured logging, backup, monitoring, and scheduler settings.
- `backend/app/core/database.py`: Configure SQLite WAL journal mode and connection pooling pragmas.
- `backend/main.py`: Attach structured logging middleware, correlation ID tracking, centralized exception handlers, enhanced health router, and scheduler lifespan.
- `backend/requirements.txt`: Ensure necessary lightweight standard utilities are documented.

### Files to Create
- `backend/app/core/logging_config.py`: Centralized structured JSON logger with PII / credential redaction.
- `backend/app/core/scheduler.py`: Lightweight background maintenance scheduler (safe, idempotent tasks).
- `backend/app/services/health_service.py`: Deep health diagnostics (DB ping, disk space, memory, service status).
- `backend/app/services/backup_service.py`: Automated SQLite online backup, verification, and rotation.
- `backend/app/services/ai_monitoring_service.py`: Provider latency, timeout, circuit breaker, and token tracking.
- `backend/app/api/v1/endpoints/health.py`: Comprehensive `/api/health` and `/api/health/detailed` (admin-gated).
- `backend/app/api/v1/endpoints/admin_maintenance.py`: Administrative maintenance endpoints (trigger backup, view logs summary, AI telemetry, review reminders).
- `backend/tests/test_phase18_maintenance.py`: Comprehensive automated tests for health checks, logging redaction, error handling, backup/recovery, and AI monitoring.
- `docs/phase-18/*`: 12 comprehensive operational and technical documentation files.

---

## 11. Recommended Implementation Strategy

We will implement Phase 18 in controlled, non-destructive stages:
1. **Stage 1: Core Logging & Correlation Middleware** — Establish structured JSON logging with strict regex redaction for tokens, passwords, and sensitive questionnaire inputs.
2. **Stage 2: Application & Database Health Monitoring** — Deploy tiered health endpoints (`/api/health` public, `/api/health/detailed` admin-gated) testing live database responsiveness.
3. **Stage 3: Centralized Error Monitoring & Diagnostics** — Standardize exception responses with correlation IDs and error classification.
4. **Stage 4: Database Reliability & Automated Backup Service** — Implement online SQLite backup with integrity verification, checksumming, and retention pruning.
5. **Stage 5: Clinical Content & Rule Review Tracking** — Add maintenance helper routines to detect content/rules nearing clinical review deadlines.
6. **Stage 6: AI Service Reliability & Monitoring** — Create an AI monitoring circuit breaker with token accounting, latency metrics, and deterministic fallback guards.
7. **Stage 7: Periodic Maintenance Scheduler** — Implement an asynchronous background maintenance runner for log rotation, backup schedules, and review checks.
8. **Stage 8: Comprehensive Documentation Suite** — Generate all 12 operational runbooks in `docs/phase-18/`.
9. **Stage 9: Automated Test Suite & Regression Verification** — Run full pytest suite ensuring 100% pass rate.
