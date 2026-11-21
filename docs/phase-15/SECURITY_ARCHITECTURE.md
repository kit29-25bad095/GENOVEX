# GENOVEX — PHASE 15: SECURITY ARCHITECTURE SPECIFICATION
## Comprehensive Defense-in-Depth, Cryptographic Protocols & Access Control

### 1. Executive Security Overview
GENOVEX is an AI-assisted male reproductive health risk identification and clinical navigation platform tailored to the United Arab Emirates healthcare ecosystem. Because male fertility, sexual health, and testicular concerns represent some of the most sensitive personal health data (PHI), GENOVEX implements a defense-in-depth architecture designed around data minimization, strict isolation of concerns, and verifiable zero-trust boundaries.

```
+---------------------------------------------------------------------------------------+
|                                    PERIMETER LAYER                                    |
|   Strict HTTPS (TLS 1.3), HSTS Preload (63072000s), RFC 1123 Hostname Validation     |
|   CORS Fail-Closed, CSP (No-eval, Frame-Ancestors 'none'), Permissions-Policy        |
+-------------------------------------------+-------------------------------------------+
                                            |
                                            v
+---------------------------------------------------------------------------------------+
|                                APPLICATION & API LAYER                                |
|   FastAPI, Request Size Limiter (2MB DoS Shield), Starlette Correlation ID Tracking    |
|   Docs Disabled in Production (docs_url=None), Simulated Auth Dev-Only Guard          |
+-------------------------------------------+-------------------------------------------+
                                            |
                                            v
+---------------------------------------------------------------------------------------+
|                            IDENTITY & ACCESS CONTROL (RBAC)                           |
|   NIST SP 800-132 PBKDF2-SHA256 Password Hashing (10+ char policy)                    |
|   JWT (HS256) Bearer Auth, JTI/Token Revocation Blacklist, In-Memory Brute-Force      |
|   Rate Limiter (5 failed attempts -> 15 min lockout), Object-Level Assessment Checks   |
+-------------------------------------------+-------------------------------------------+
                                            |
                                            v
+---------------------------------------------------------------------------------------+
|                             HEALTH DATA & AUDIT TRAIL LAYER                           |
|   Pseudonymous Assessment Sessions (Zero PII required for assessment)                |
|   Automated Sensitive Field Sanitization (Passwords, PHI, Tokens -> [REDACTED])      |
|   Immutable AuditLog Records for Security, Content CMS, and Clinical Review Events   |
+-------------------------------------------+-------------------------------------------+
                                            |
                                            v
+---------------------------------------------------------------------------------------+
|                                  DATABASE & STORAGE                                   |
|   SQLite 3 WAL (Development) / Managed PostgreSQL (Production Target, UAE Region)     |
|   Encrypted Backups, SHA-256 Checksum Verification, Least Privilege Connection        |
+---------------------------------------------------------------------------------------+
```

---

### 2. Network & Perimeter Security Controls

#### 2.1 Transport Layer Security (TLS)
- **Minimum Protocol:** TLS 1.2; Enforced TLS 1.3 for all production deployments.
- **HSTS Enforcement:** `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload` header injected by both Next.js edge and FastAPI ASGI middleware.
- **Cipher Suites:** Restrictive modern cipher suite ordering prioritizing `TLS_AES_256_GCM_SHA384` and `TLS_CHACHA20_POLY1305_SHA256`.

#### 2.2 Content Security Policy (CSP) & Browser Protection
- **Frame Ancestors:** `frame-ancestors 'none'` prevents any clickjacking or framing of the application.
- **MIME Sniffing Prevention:** `X-Content-Type-Options: nosniff`.
- **Cross-Site Scripting (XSS):** `X-XSS-Protection: 1; mode=block`.
- **Referrer Privacy:** `Referrer-Policy: strict-origin-when-cross-origin` ensures patient assessment query parameters and tokens are never leaked to external referrers.
- **Hardware Privacy:** `Permissions-Policy: camera=(), microphone=(), geolocation=()` blocks unsolicited sensor access.

#### 2.3 Cross-Origin Resource Sharing (CORS) Architecture
- **Fail-Closed Principle:** Any origin not explicitly validated against RFC 1123 production standards is rejected.
- **Wildcard Prohibition:** Wildcards (`*`) are strictly prohibited in all staging and production profiles.
- **Localhost Prohibition:** Staging and production configurations reject loopback addresses (`localhost`, `127.0.0.1`, `::1`).

---

### 3. Authentication & Credential Management

#### 3.1 Password Policy & Storage
- **Algorithm:** PBKDF2 with HMAC-SHA256, conforming to NIST Special Publication 800-132 recommendations.
- **Password Complexity Engine (`validate_password_complexity`):**
  - Minimum length: 10 characters.
  - Requires at least 1 uppercase letter (`[A-Z]`).
  - Requires at least 1 lowercase letter (`[a-z]`).
  - Requires at least 1 numerical digit (`[0-9]`).
  - Requires at least 1 special character (`[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\/`~]`).
  - Denies common/dictionary passwords (e.g., `password123`, `admin12345`).

#### 3.2 Brute-Force Rate Limiting & Account Lockout
- **Threshold:** Maximum 5 consecutive failed login attempts per account/email key.
- **Lockout Duration:** 15 minutes (`LOCKOUT_DURATION_MINUTES = 15`).
- **Architecture:** Dual-layer defense:
  1. High-speed in-memory thread-safe `LoginAttemptTracker` with sliding-window time tracking.
  2. Database-backed `failed_login_attempts` counter and `locked_until` timestamp on the `User` model, ensuring lockout persistence across application worker recycles.
- **Audit Logging:** Every failed attempt emits `USER_LOGIN_FAILED`, and reaching the threshold emits `USER_ACCOUNT_LOCKED`.

#### 3.3 JWT Session Lifecycle & Revocation
- **Algorithm:** HMAC-SHA256 (`HS256`) signed with a cryptographically secure random `SECRET_KEY`.
- **Token Invalidation on Logout:** Immediate insertion into in-memory `REVOKED_TOKENS` blacklist.
- **Token Invalidation on Password Reset:** Updating `password_changed_at` on the user record automatically renders all previously issued tokens invalid.
- **Token Claims:** Minimal claims: `sub` (email), `role` (RoleEnum), `uid` (integer ID), `exp` (expiration), and `iat` (issued-at timestamp). Zero clinical data or PHI is stored inside JWT tokens.

---

### 4. Role-Based Access Control (RBAC) Matrix

| Resource / Action | PATIENT | CLINICIAN | ADMIN | SUPERADMIN |
|---|:---:|:---:|:---:|:---:|
| **Public Health Library & Landing** | Read | Read | Read | Read |
| **Start / Resume Anonymous Assessment** | Execute | Execute | Execute | Execute |
| **View Own Assessment Report** | Read (Own) | Read (Assigned) | Read (Audit) | Full |
| **Clinician Portal Dashboard & Queue** | Denied (403) | Read | Read | Full |
| **Perform Clinical Review & Add Notes** | Denied (403) | Execute | Execute | Full |
| **Medical Content CMS (Draft/Edit)** | Denied (403) | Author | Author/Manage | Full |
| **Clinical Rule Authoring & Approval** | Denied (403) | Review/Approve | Manage | Full |
| **User Role Assignment & Status** | Denied (403) | Denied (403) | Manage (Non-SA) | Full |
| **Assign SUPERADMIN Role** | Denied (403) | Denied (403) | Denied (403) | Full |
| **System Audit Logs Inspection** | Denied (403) | Denied (403) | Read | Full |
| **System Diagnostics & Maintenance** | Denied (403) | Denied (403) | Read/Trigger | Full |

---

### 5. Object-Level Access Control (IDOR Mitigation)

- **Assessment Isolation:** A patient user can only evaluate or retrieve an assessment where `assessment.user_id == current_user.id` or via valid cryptographic `session_token`.
- **Session Token Comparison:** Evaluated using constant-time `hmac.compare_digest` to prevent timing attacks.
- **Centralized Clinical Governance Gate:** `ClinicalGovernanceGate.verify_assessment_ownership` enforces server-side ownership checks across all report compilation, evaluation, and navigation endpoints. Zero client-controlled query parameter overrides exist.

---

### 6. Sensitive Data Sanitization & Audit Trails

- **Sanitization Engine (`sanitize_audit_details`):**
  Recursively traverses all audit log detail dictionaries and replaces sensitive keys with `"[REDACTED]"`.
  Protected keys include:
  `password`, `hashed_password`, `token`, `access_token`, `secret`, `session_token`, `csrf_token`, `answers`, `responses`, `medical_notes`, `confidential_notes`, `notes`, `patient_notes`, `history`, `ssn`, `emirates_id`, `phone_number`.
- **Zero Plaintext Logging:** FastAPI request logging middleware strictly excludes request bodies and tokens from standard output and disk log files.
- **Immutable Log Storage:** `audit_logs` table records actor ID, actor email, assigned role, action code, resource type, resource ID, client IP, and UTC timestamp.
