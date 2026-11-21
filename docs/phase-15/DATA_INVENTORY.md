# GENOVEX — PHASE 15: DATA INVENTORY & CLASSIFICATION
## Comprehensive Catalog of Data Assets, Lifecycle, and Protection Controls

### 1. Overview & Data Classification Scheme
To comply with the UAE Personal Data Protection Law (Federal Decree-Law No. 45 of 2021) and the UAE Health Data Law (Federal Law No. 2 of 2019), all data processed within GENOVEX is classified into four distinct sensitivity tiers:

1. **Category 1: Public / Open Data (Unrestricted)**
   - Medical knowledgebase articles, educational glossaries, clinical references, public facility directory data, open-source software license notices.
2. **Category 2: Operational & Technical Metadata (Internal)**
   - API correlation IDs, HTTP route request durations, application error codes, system uptime metrics, anonymized circuit breaker failure counts.
3. **Category 3: Personal Identifiable Information (PII) (Confidential)**
   - User account email address, full name, clinician professional license number (DHA/DoH/MOHAP), IP address in security logs, user account creation timestamps.
4. **Category 4: Special Category / Sensitive Personal Health Data (Highly Confidential)**
   - Male reproductive questionnaire responses, erectile and ejaculatory duration data, testicular history (undescended testis, varicocele, trauma), fertility status, triggered clinical rules snapshot, non-diagnostic clinical triage outcome tiers.

---

### 2. Comprehensive Data Element Catalog

| Data Element | Category | Storage Location | Retention / Lifecycle | Encryption at Rest | Encryption in Transit | Access Authorization |
|---|:---:|---|---|:---:|:---:|---|
| **User Email** | PII | `users.email` (SQLite/PostgreSQL) | Active account life + statutory retention | AES-256 (PostgreSQL) / OS-level | TLS 1.3 | User, Admin, SuperAdmin |
| **Password Hash** | PII | `users.hashed_password` | Active account life; salted PBKDF2-SHA256 | Hashed with unique salt | TLS 1.3 | Authentication system only (never revealed) |
| **User Full Name** | PII | `users.full_name` | Active account life | AES-256 (PostgreSQL) / OS-level | TLS 1.3 | User, Clinician (if shared), Admin |
| **Clinician DHA/DoH License** | PII | `users.credentials_summary` | Active clinician profile life | AES-256 (PostgreSQL) / OS-level | TLS 1.3 | Clinician, Admin, SuperAdmin |
| **Failed Login Counter** | Technical | `users.failed_login_attempts` | Resets upon successful login or after 15 min | Columnar | TLS 1.3 | System / Admin |
| **Account Lockout Expiry** | Technical | `users.locked_until` | Cleared upon lockout expiration | Columnar | TLS 1.3 | System / Admin |
| **Session Token (Guest)** | Pseudonymous | `assessments.session_token` | Active draft or until report locked | Cryptographic random hex (32-byte) | TLS 1.3 | Anonymous session holder |
| **Questionnaire Responses** | Health Data (Cat 4) | `assessment_responses.response_value` | Immutable snapshot pinned to report | JSON / AES-256 at storage volume | TLS 1.3 | Session Owner, Clinician (if shared) |
| **Clinical Rule Trigger Snapshot** | Health Data (Cat 4) | `assessment_reports.triggered_rules_snapshot_json` | Permanent clinical snapshot for reproducibility | JSON / AES-256 at storage volume | TLS 1.3 | Session Owner, Clinician (if shared) |
| **Clinical Outcome Tier** | Health Data (Cat 4) | `assessment_reports.outcome_tier` | Permanent clinical snapshot | Enum / AES-256 | TLS 1.3 | Session Owner, Clinician (if shared) |
| **Urgent Red-Flag Indicator** | Health Data (Cat 4) | `assessment_reports.is_urgent_red_flag` | Permanent clinical snapshot | Boolean / AES-256 | TLS 1.3 | Session Owner, Clinician, System |
| **Clinician Internal Notes** | Health Data (Cat 4) | `audit_logs.details` (Confidential) | Permanent audit record | Sanitized JSON | TLS 1.3 | Reviewing Clinician, SuperAdmin |
| **Security Audit Logs** | Technical / PII | `audit_logs` | 12-month rolling retention | Redacted JSON / AES-256 | TLS 1.3 | Admin, SuperAdmin |
| **Database Backups** | Full Set | `./backend/backups` / S3 me-central-1 | 7 rolling daily snapshots | AES-256 GCM encrypted tarball | TLS 1.3 | Automated backup engine, DevOps Lead |

---

### 3. Data Flow & Boundary Mapping

```
[Patient Device (Browser)]
           |
           | TLS 1.3 (HTTPS) - Strict Origin, CSP, HSTS
           v
[Edge / Reverse Proxy (Vercel / Next.js Rewrite)]
           |
           | TLS 1.3 (Internal / HTTPS)
           v
[FastAPI Application Backend]
    |                  |
    | (Zero PHI)       | (Direct SQL Query via SQLAlchemy)
    v                  v
[AI Client Service]   [Primary Database (PostgreSQL / SQLite WAL)]
    |                  |
    | (Only anonymized | (Encrypted at rest, AES-256)
    | educational      v
    | findings)       [Encrypted Automated Backups (UAE Region: me-central-1)]
    v
[AI Provider: Gemini/OpenAI] (Zero Data Retention / ZDR configured)
```

---

### 4. Data Minimization Principles Implemented

1. **No Mandatory Personal Identifiers for Risk Assessment:**
   Patients can complete the 11-domain assessment and generate their report entirely anonymously using pseudonymous session tokens. Full legal names, national civil IDs (Emirates ID), and telephone numbers are NEVER required to receive clinical risk triage.
2. **Deterministic Processing without External Dependency:**
   Risk factor identification and emergency red-flag triaging are executed 100% locally by the deterministic Python clinical rule engine. No patient answers are transmitted to cloud AI providers to calculate risk tiers.
3. **No Advertising or Analytics Tracking:**
   No third-party behavioral trackers (Google Analytics, Meta Pixel, Hotjar) are installed or permitted in the application code.
