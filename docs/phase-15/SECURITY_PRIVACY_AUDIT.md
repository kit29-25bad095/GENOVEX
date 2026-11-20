# GENOVEX: SECURITY & PRIVACY AUDIT REPORT
## Comprehensive Technical Security Assessment & Privacy Architecture Review

**Project:** GENOVEX – Male Reproductive Health Risk Identification & Clinical Navigation Platform  
**Roadmap Phase:** Phase 15 – Security, Privacy & Regulatory  
**Audit Date:** 20 November 2026  
**Auditor:** Application Security Engineer & Healthcare Data Protection Officer  
**Scope:** Full-Stack Security Controls, Cryptography, Privacy Workflows & Vulnerability Assessment

---

## 1. Executive Summary

This security and privacy audit evaluates the integrated GENOVEX application across its architectural tiers: Next.js frontend, FastAPI backend, SQLite/PostgreSQL database layers, authentication protocols, and clinical governance enforcement gates. As a male reproductive health platform handling sensitive personal health information (PHI/PII), GENOVEX enforces zero-trust architecture, defensive role-based access control, cryptographic password hashing, data minimization, and automated privacy erasure workflows.

---

## 2. Technical Security Controls Evaluation

### 2.1 Authentication & Session Management
- **Password Hashing:** Passwords are hashed using NIST-approved PBKDF2-SHA256 (`schemes=["pbkdf2_sha256"]` with 29,000 rounds) via Passlib. Passwords in `users` are never stored in plaintext or reversible formats.
- **JWT Token Issuance:** Authenticated sessions issue JSON Web Tokens (JWT) signed with HMAC-SHA256 (`HS256`) using server-side secrets (`settings.SECRET_KEY`).
- **Token Expiry & Revocation:** Access tokens have an expiration of 24 hours. Token payloads contain standard claims: subject (`sub` email), role (`role`), and user ID (`uid`). Account deactivation (`is_active = False`) terminates session renewal across all protected endpoints.
- **Password Complexity:** Enforces minimum 8-character passwords and requires verification of current password during rotation (`POST /api/v1/auth/change-password`).

### 2.2 Role-Based Access Control (RBAC) & Privilege Separation
The platform enforces a four-tier role hierarchy:
1. `PATIENT`: Access restricted to self-initiated assessments, personal questionnaire responses, self-claimed historical reports, and public health library. Blocked from administrative, clinician, and cross-user records.
2. `CLINICIAN`: Authorized for shared review queue (`/api/v1/clinician/*`), clinical review notes, and clinical audit inspection. Blocked from system administration, rule approval, and user role modifications.
3. `ADMIN`: Authorized for operational dashboard (`/api/v1/admin/*`), system health, user activation toggling, and audit log inspection. Blocked from clinical review notes, clinical rule publishing, and SuperAdmin role elevation.
4. `SUPERADMIN`: Highest operational tier. Holds exclusive authority for user role modification (`PUT /api/v1/admin/users/{id}/role`). Protected by final active superadmin lockout invariant.

### 2.3 Horizontal Access Control & Insecure Direct Object References (IDOR)
- **Assessment History:** `GET /api/v1/assessment/history` queries strictly by `Assessment.user_id == current_user.id`. Callers cannot supply an arbitrary `user_id`.
- **Assessment Ownership Verification:** `ClinicalGovernanceGate.verify_assessment_ownership` compares caller identity against assessment records. If an assessment is bound to another user, requests are rejected with **HTTP 403 Forbidden**.
- **Assessment Claiming:** `POST /api/v1/assessment/{session_token}/claim` prevents claiming any session already linked to another registered account.

### 2.4 Server-Side Input Validation & Injection Defenses
- **SQL Injection:** 100% of database interactions utilize SQLAlchemy ORM with parameterized queries. Raw string formatting or unescaped SQL concatenation is strictly prohibited.
- **Schema Validation:** FastAPI and Pydantic v2 automatically validate request payloads, query parameters, and data types before executing service methods. Invalid payloads fail with **HTTP 422 Unprocessable Content**.
- **Resource Exhaustion Bounds:** Query pagination parameters (`limit`, `page_size`) enforce strict upper bounds (`le=100`), preventing denial-of-service via large query memory dumps.

### 2.5 Cross-Origin Resource Sharing (CORS) & Browser Security
- CORS headers are configured in `backend/main.py` via `CORSMiddleware`.
- Precedence is governed by environment settings (`ALLOWED_CORS_ORIGINS`). Local developer origins (`http://localhost:3000`, `http://127.0.0.1:3000`) are strictly restricted in production environments.

### 2.6 Sensitive Data Minimization & Redaction
- **Zero-PII Telemetry:** Admin and clinician telemetry endpoints (`/api/v1/admin/overview`, `/api/v1/admin/assessments/stats`, `/api/v1/clinician/queue`) return categorical counts and aggregated metrics. Zero patient demographic details, emails, or free-text answers are joined.
- **Audit Logging Redaction:** Audit log details exclude passwords, raw cryptographic tokens, and sensitive clinical answers.

---

## 3. Privacy Architecture & Data Subject Rights

In compliance with UAE Federal Decree-Law No. 45 of 2021 on Personal Data Protection and international privacy regulations:

### 3.1 Right of Access & Data Portability
- Endpoint: `GET /api/v1/auth/privacy/export-data`
- Returns a structured, machine-readable JSON export containing:
  - Account profile metadata (ID, email, name, role, registration timestamp).
  - List of associated assessments (UUID, session token, lifecycle status, start/submission timestamps).
  - Explicit attribution to the UAE Personal Data Protection Law.

### 3.2 Right to Erasure / Right to be Forgotten
- Endpoint: `POST /api/v1/auth/privacy/delete-account`
- Requires explicit query confirmation (`confirm=true`).
- Execution workflow:
  1. Deactivates user account (`is_active = False`).
  2. Permanently anonymizes email: `deleted_user_{id}_{timestamp}@redacted.local`.
  3. Redacts full name: `"Redacted User"`.
  4. Preserves clinical and security audit records while stripping identifiable personal linkages.
  5. Enforces safety lockout: The final active `SUPERADMIN` cannot delete their account, preventing administrative orphan states.

---

## 4. Cryptographic Baseline & Database Backup Provenance

- **Authoritative Database Path:** `backend/genovex.db`
- **File Size:** `4,993,024` bytes
- **SHA-256 Hash:** `BF94EFBBF22FC1BF4769C26C8BB36198F62E886F90D01962C314284D60D534BA`
- **Verification Status:** Unmutated across all test cycles. Automated test suites execute exclusively against dynamic disposable sandbox copies managed by `conftest.py`.
- **Disaster Recovery Baseline:** Pristine Tier 1 backup preserved at `backend/backups/genovex_backup_tier1_20261120_020738.db` (`AC10A688BD070AB0F4D90E77C5055714E634C8AED51F68C02E12909FE3EF5A09`).

---

## 5. Summary of Findings & Action Items

| Category | Finding | Current State | Risk Level | Recommended Action |
| :--- | :--- | :---: | :---: | :--- |
| **Authentication** | Password hashing | PBKDF2-SHA256 | LOW | Maintained. |
| **RBAC** | Admin vs Clinician separation | Strict role dependencies | LOW | Maintained. |
| **Data Protection**| User data erasure workflow | Automated anonymization | LOW | Maintained. |
| **Infrastructure** | Database encryption-at-rest | SQLite filesystem | MEDIUM | Transition to encrypted SQLite (SQLCipher) or managed PostgreSQL on AWS/Azure UAE for production launch. |
| **Rate Limiting** | Slowloris / API brute-force | Basic middleware | MEDIUM | Deploy Redis-backed rate limiter on production reverse proxy (Nginx / Cloudflare). |
