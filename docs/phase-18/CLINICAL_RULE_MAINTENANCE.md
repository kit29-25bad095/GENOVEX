# GENOVEX Clinical Rule Maintenance Specification

## 1. Governance Principles for Deterministic Clinical Rules

Clinical rules within GENOVEX translate male reproductive health risk factors (e.g., severe cryptorchidism history, anabolic steroid use, occupational heat/toxin exposure, painless testicular masses) into validated clinical risk tiers:
- **Tier 1:** No Reported Risk Factors Identified (Includes mandatory disclaimer that normal fertility is not proven).
- **Tier 2:** Modifiable / Lifestyle Risk Factors Identified.
- **Tier 3:** Clinical Evaluation Recommended (Andrology, Urology, Reproductive Endocrinology).
- **Tier 4:** Urgent Safety Circuit (Painless testicular lump, persistent hematuria, severe acute symptoms).

Because clinical guidelines from AUA (American Urological Association), EAU (European Association of Urology), and UAE health authorities (DHA, DOH) are periodically updated, rule maintenance must adhere to strict deterministic and legal safeguards.

---

## 2. Independent Rule Versioning Architecture

1. **Rule Version Lifecycle:**
   - Every rule is tracked with a semantic version (e.g., `v1.0.0`).
   - Changes to trigger logic, required answer values, or clinical outcome tiers require authoring a new version record.
2. **Review Records & Audit Immutability:**
   - Clinical rule modifications require review by a licensed clinician (`CLINICIAN` or `SUPERADMIN`).
   - The system logs the approving clinician's user ID, license summary, approval timestamp, and evidence rationale into `clinical_rule_version_records`.
3. **Draft -> Review -> Published Workflow:**
   - Active rules must have `status == PUBLISHED`.
   - Rules in `DRAFT` or `UNDER_REVIEW` are completely ignored during live assessment report evaluation.

---

## 3. Immutability of Historical Assessment Reports

A paramount medical-legal requirement of GENOVEX is that past patient reports must remain permanently reproducible:
- When an assessment is compiled, the system captures a frozen snapshot of:
  - Exact user responses.
  - Active rules that triggered.
  - Rule engine version tag.
  - Outcome tier and generated clinical narrative.
- **Invariant:** Even if a clinical rule is modified, upgraded to `v2.0.0`, or retired in the future, previously generated assessment reports are **never re-evaluated dynamically**. Querying an existing session token returns the authentic, frozen historical report snapshot.

---

## 4. Rule Staleness Auditing

- The maintenance service monitors the `last_reviewed_at` timestamp for all active rules against the **365-day review cycle**.
- Rules lacking a formal re-review within 365 days are surfaced on administrative telemetry dashboards (`GET /api/v1/admin/maintenance/clinical-assets`) to ensure clinical leadership initiates re-validation.
