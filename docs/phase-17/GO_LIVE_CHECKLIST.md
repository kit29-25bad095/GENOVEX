# GENOVEX — PHASE 17: PRODUCTION GO-LIVE CHECKLIST
## Pre-Launch Verification, Gate Sign-Offs, and Operational Readiness Criteria

### 1. Multi-Stakeholder Sign-Off Gates

Before declaring GENOVEX ready for public patient access in the United Arab Emirates, each designated domain owner must execute and document their formal sign-off:

```
[ CLINICAL GOVERNANCE GATE ]   --> Signed off by Chief Medical Officer (CMO)
[ CYBERSECURITY & AUDIT GATE ] --> Signed off by Lead Security Architect (CISO)
[ DATA RESIDENCY & LEGAL GATE] --> Signed off by UAE Healthcare Legal Counsel
[ CLOUD INFRASTRUCTURE GATE ]  --> Signed off by Principal DevOps Engineer
[ PRODUCT & QUALITY GATE ]     --> Signed off by Lead Full-Stack Engineer
```

---

### 2. Comprehensive Pre-Go-Live Checklist

#### Section A: Frontend & User Interface Verification
- [x] **Next.js Production Build:** Succeeded with zero errors across all 19 application routes.
- [x] **Vercel Edge Deployment:** Live and accessible at `https://genovex.vercel.app` (HTTP 200).
- [x] **Bilingual Support:** Complete English (LTR) and Arabic (RTL) localization verified.
- [x] **Client-Side Secrets:** Zero environment secrets bundled into client JavaScript.
- [x] **Security Headers:** Strict CSP, HSTS preload, X-Content-Type-Options, and X-Frame-Options active.
- [ ] **Custom Domain Binding:** Bind `www.genovex.ae` and `genovex.ae` to Vercel production project (Pending DNS delegation).

#### Section B: Backend Infrastructure & API Verification
- [x] **FastAPI Application Stack:** Fully implemented with lifespan events and structured logging.
- [x] **Process Supervision:** Gunicorn + Uvicorn worker supervisor configured in `backend/gunicorn_conf.py`.
- [x] **Security Headers Middleware:** Added nosniff, DENY, CSP, and HSTS to FastAPI responses.
- [x] **DoS Protection:** 2MB request payload size limiter active.
- [x] **Production API Shielding:** Swagger UI (`/docs`) and OpenAPI JSON (`/openapi.json`) disabled in production mode.
- [ ] **Sovereign Cloud Deployment:** Deploy containerized backend to AWS UAE (`me-central-1` Dubai) ECS Fargate. *(BLOCKER)*
- [ ] **Production Health Probe:** Verify live `GET https://api.genovex.ae/health/live` returns HTTP 200. *(BLOCKER)*

#### Section C: Database & Data Residency Verification
- [x] **Database Schema:** 17 tables and 40 facility columns synchronized via Alembic.
- [x] **Security Migrations:** `0003_phase15_security_enhancements` applied (lockout & password timestamps).
- [ ] **Provision Sovereign RDS:** Provision Amazon RDS for PostgreSQL 16 Multi-AZ in `me-central-1`. *(BLOCKER)*
- [ ] **PostgreSQL Migration Execution:** Execute `alembic upgrade head` against production PostgreSQL instance. *(BLOCKER)*
- [ ] **Automated Backup Schedule:** Configure automated daily RDS snapshots + encrypted UAE S3 bucket replication. *(BLOCKER)*
- [ ] **Backup Restore Test:** Execute end-to-end database restore verification test. *(BLOCKER)*

#### Section D: Identity, Access Control & Brute-Force Defense
- [x] **Password Complexity:** Enforced (10+ characters, upper, lower, digit, special character).
- [x] **Brute-Force Rate Limiting:** 5 consecutive failures trigger 15-minute lockout (tested).
- [x] **Session Revocation:** `/auth/logout` actively revokes tokens; password change invalidates prior tokens.
- [x] **Role-Based Access Control:** Strict separation across Patient, Clinician, Admin, and SuperAdmin.
- [x] **Object-Level Access Control:** IDOR prevention verified; patients cannot access assessments of others.
- [x] **Simulated Auth Guard:** `ALLOW_SIMULATED_AUTH` strictly rejected if `ENVIRONMENT=production`.

#### Section E: Clinical Determinism & Medical Boundaries
- [x] **Pure Deterministic Rule Engine:** Clinical outcome tiers (1 to 4) evaluated by pure Python DAG without LLM drift.
- [x] **Urgent Red-Flag Golden Window:** Acute scrotal symptoms route directly to emergency triage and UAE Ambulance 998.
- [x] **Non-Diagnostic Scope Limitation:** Prominent bilingual disclaimers stating GENOVEX does not diagnose infertility or prescribe medications.
- [x] **Frozen Report Snapshots:** Assessment reports remain immutable historical records.

#### Section F: UAE Legal & Regulatory Compliance
- [x] **3-Tier Consent Architecture:** Explicit separation of Platform Terms, Sensitive Health Data Processing, and Clinician Sharing.
- [x] **Software Licensing Attribution:** Public disclosure of MIT, Apache 2.0, PSF, PostgreSQL licenses and OpenAI API terms.
- [ ] **UAE Legal Counsel Review:** Formal sign-off on bilingual Terms of Service and Privacy Policy. *(PRE-REQUISITE)*
- [ ] **Health Authority Notification:** Formal confirmation of SaMD non-diagnostic classification with MOHAP/DHA. *(PRE-REQUISITE)*

---

### 3. Go-Live Decision Matrix

| Domain | Status | Owner Sign-Off Required |
|---|:---:|---|
| **Presentation & UI** | **GO** | Frontend Lead |
| **Security & Privacy** | **GO** | Lead Security Architect |
| **Clinical Decision Logic** | **GO** | Chief Medical Officer |
| **Backend & Database Hosting** | **NO-GO (Pending UAE Cloud Provisioning)** | DevOps Lead |
| **UAE Legal & Regulatory** | **NO-GO (Pending Formal Legal Sign-Off)** | Legal Counsel |

**Final Go-Live Recommendation:**
Hold public launch until AWS UAE (`me-central-1`) backend and database provisioning are completed and verified.
