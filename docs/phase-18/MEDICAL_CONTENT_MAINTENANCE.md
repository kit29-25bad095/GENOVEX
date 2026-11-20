# GENOVEX Medical Content Maintenance Specification

## 1. Overview & Clinical Content Architecture

GENOVEX provides public and clinical education on male reproductive conditions (e.g., Varicocele, Hypogonadism, Obstructive Azoospermia, Erectile Dysfunction, Cryptorchidism). Because medical literature evolves and UAE regulatory guidelines (DHA, DOH, MoHAP) update over time, educational content requires structured lifecycle maintenance.

---

## 2. Content Review Validity Window (The 365-Day Rule)

- **Review Policy:** All published medical condition content is subject to mandatory clinical re-evaluation every **365 days** (configured via `CLINICAL_REVIEW_VALIDITY_DAYS = 365`).
- **Staleness Flagging:**
  - The maintenance audit service evaluates `ConditionContent.last_reviewed_at`.
  - Content exceeding 365 days without a formal re-review is flagged as `STALE_REVIEW` in administrative diagnostics.
  - While stale content remains accessible in the public Health Library to prevent educational disruption, notifications alert clinical administrators to initiate review.

---

## 3. Structured Clinical Review Workflow

```
[ DRAFT ]
    │
    ▼ (Author submits content update)
[ SUBMITTED FOR REVIEW ]
    │
    ├─────────────────────────────┐
    ▼ (Authorized Clinician)      ▼ (Revision Needed)
[ APPROVED ]                   [ REJECTED / CHANGES REQUESTED ]
    │
    ▼ (Publishing Action)
[ PUBLISHED ] (Live in Public Library)
    │
    ▼ (Superseded or Decommissioned)
[ ARCHIVED ]
```

### 3.1 Role Authorization Safeguards
- **Authors / Editors:** Can create drafts and edit draft translations.
- **Clinical Reviewers (`CLINICIAN`, `SUPERADMIN`):** Only accredited clinicians possessing recognized credentials (e.g., DHA/DOH license numbers) may execute approval transitions.
- **Publishers (`ADMIN`, `SUPERADMIN`):** Transition approved content to public visibility.

---

## 4. Semantic Versioning & Version History Restoration

1. **Immutable Historical Versions:**
   - Every modification creates a new incremented entry in `content_versions` with the editor's identity, timestamp, and modification summary.
2. **Safe Rollback Mechanism:**
   - Restoring a previous version never deletes history.
   - Instead, the system fetches the selected historical version payload and creates a *new* version record with an audit tag (`RESTORED_FROM_V{n}`).
   - This ensures a complete, unbroken chronological audit trail for clinical governance.

---

## 5. Architectural Decoupling from Clinical Rules

Medical Content (educational descriptions, anatomical explanations, patient lifestyle advice) is strictly decoupled from the Deterministic Clinical Rule Engine:
- Editing a medical condition's description in the CMS **never** changes assessment questionnaire evaluation or risk tier stratifications.
- The rule engine evaluates formal questionnaire answers against coded clinical rules independently of CMS prose.
