# GENOVEX — PHASE 15: PRIVACY GOVERNANCE & CONSENT FRAMEWORK
## Patient Rights, Consent Architecture, and UAE Privacy by Design

### 1. Privacy-by-Design Governance Structure
GENOVEX adheres to the core tenets of Privacy by Design (PbD) as recognized under international healthcare informatics guidelines and the UAE Personal Data Protection Law (Federal Decree-Law No. 45 of 2021). The platform architecture enforces privacy as the default state across all endpoints.

```
+---------------------------------------------------------------------------------------+
|                                THREE-TIER CONSENT MODEL                               |
+---------------------------------------------------------------------------------------+
|  [TIER 1: PLATFORM USE & NON-DIAGNOSTIC TERMS]                                        |
|  - Scope: General terms of use, educational boundary disclosure.                      |
|  - Requirement: Mandatory prior to starting the questionnaire.                        |
|                                                                                       |
|  [TIER 2: SENSITIVE HEALTH DATA PROCESSING CONSENT]                                   |
|  - Scope: Explicit agreement to process reproductive health questionnaire answers      |
|    strictly to generate deterministic risk factor reports.                            |
|  - Requirement: Explicit affirmative consent checkbox prior to questionnaire submission.|
|                                                                                       |
|  [TIER 3: CLINICIAN & FACILITY REFERRAL SHARING CONSENT]                              |
|  - Scope: Voluntary consent to transmit assessment report snapshot to a verified     |
|    licensed UAE clinician or healthcare facility for consultation review.             |
|  - Requirement: Granular, fully optional, revocable consent per interaction.         |
+---------------------------------------------------------------------------------------+
```

---

### 2. Granular Three-Tier Consent Architecture

#### 2.1 Tier 1: Platform Terms & Non-Diagnostic Decision Support Consent
- **Purpose:** Informs the user that GENOVEX provides informational risk triage, does not diagnose infertility, does not prescribe drugs, and does not replace in-person physical clinical examinations or laboratory semen analysis.
- **Enforcement:** Surfaced prominently on the assessment initiation view and in the Privacy Policy (`frontend/app/privacy/page.tsx`).

#### 2.2 Tier 2: Health Data Processing Consent
- **Purpose:** Complies with Article 5 and Article 6 of UAE PDPL requiring explicit, affirmative consent for the processing of sensitive personal health data.
- **Enforcement:** Users cannot trigger report compilation without affirming consent to process questionnaire answers for algorithmic risk stratification.

#### 2.3 Tier 3: Voluntary Clinician & Referral Sharing Consent
- **Purpose:** Complies with patient confidentiality and medical ethics standards. Sharing an assessment with a healthcare provider or booking a referral at a facility requires separate, explicit patient authorization.
- **Enforcement:** Guest sessions and patient reports are private by default. A clinician can only review an assessment if the patient explicitly shares their assessment token or requests clinician review.

---

### 3. Patient Data Subject Rights & Execution Procedures

Under UAE Federal Decree-Law No. 45 of 2021 (PDPL), data subjects are entitled to verifiable rights regarding their stored records. GENOVEX implements the following operational procedures:

#### 3.1 Right to Access & Portability (Article 13 & 14)
- **Mechanism:** Patients can view and download their complete historical assessment reports via the bilingual patient report interface (`/assessment/report/[token]`).
- **Data Export:** Reports provide a comprehensive, reproducible snapshot containing identified risk factors, evidence citations, and responses summary in structured JSON / PDF formats.

#### 3.2 Right to Rectification (Article 15)
- **Mechanism:** In-progress questionnaire responses can be updated at any time prior to final report locking. Once locked, report snapshots remain immutable to preserve clinical audit integrity, but patients may initiate a new assessment with corrected clinical information.

#### 3.3 Right to Erasure / Deletion (Article 16)
- **Mechanism:** Patients may request deletion of their account and associated assessment sessions by emailing `privacy@genovex.health`.
- **System Execution:** Authorized administrators execute a hard purge of user records and cascade delete associated drafts from `assessments` and `assessment_responses`.
- **Clinical Exception:** Locked clinical review records and audit logs are retained for statutory clinical audit periods as required under UAE healthcare regulations, but are stripped of direct personal identifiers.

#### 3.4 Right to Consent Revocation
- **Mechanism:** Patients can withdraw consent for clinician sharing at any time. Revocation breaks the sharing link and immediately removes the assessment from clinician review queues.

---

### 4. Retention & Deletion Schedule

| Record Type | Status / Classification | Default Retention Period | Disposal Method | Statutory Basis |
|---|---|---|---|---|
| **Anonymous Draft Session** | Incomplete / Abandoned | 30 days of inactivity | Automated DB prune | Data minimization |
| **Locked Assessment Report** | Completed / Finalized | 5 years from compilation | Secure cryptographic purge | Healthcare documentation standard |
| **Clinician Review Record** | Official Clinical Interaction | 5 years from review date | Archived encrypted | DHA / MOHAP record-keeping |
| **Security Audit Logs** | Security & Compliance | 12 months rolling | Automated log rotation & deletion | ISO 27001 / OWASP standard |
| **Failed Login Tracker** | Ephemeral In-Memory | 15 minutes | Automatic memory expiration | Security baseline |
| **Revoked JWT Blacklist** | In-Memory / Ephemeral | 24 hours (token max TTL) | Automatic memory eviction | JWT lifecycle standard |

---

### 5. Privacy Officers & Contact Channels
- **Data Protection Officer (DPO):** Designated Healthcare Compliance Lead.
- **Primary Privacy Inquiries:** `privacy@genovex.health`
- **Security Incident Hotline:** `security@genovex.health`
