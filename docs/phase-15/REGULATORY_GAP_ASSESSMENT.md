# GENOVEX: REGULATORY GAP ASSESSMENT & HEALTHCARE COMPLIANCE ROADMAP
## UAE Health Data Regulations, SaMD Classification & Clinical Governance Analysis

**Project:** GENOVEX – Male Reproductive Health Risk Identification & Clinical Navigation Platform  
**Roadmap Phase:** Phase 15 – Security, Privacy & Regulatory  
**Assessment Date:** 20 November 2026  
**Auditor:** Healthcare Regulatory Specialist & Application Compliance Lead  
**Jurisdiction:** United Arab Emirates (UAE) Federal, Abu Dhabi (DoH), and Dubai (DHA)

---

## 1. Executive Notice & Legal Disclaimer

> [!IMPORTANT]
> This regulatory assessment is an engineering and compliance gap analysis prepared to guide technical development and clinical governance. It does NOT constitute formal legal advice, nor does it certify regulatory approval or medical device clearance. GENOVEX makes no claim of having received formal regulatory clearance from the UAE Ministry of Health and Prevention (MOHAP), Dubai Health Authority (DHA), or Department of Health Abu Dhabi (DoH). Formal commercial and clinical release requires submission to qualified legal counsel and accredited clinical notified bodies.

---

## 2. Applicable UAE Legislative & Regulatory Frameworks

Operating a digital health platform in the United Arab Emirates involves three primary regulatory pillars:

### 2.1 UAE Federal Law No. 2 of 2019 (ICT Health Law) & Cabinet Resolution No. 32 of 2020
- **Scope:** Governs the collection, processing, storage, and transfer of health data within the UAE.
- **Key Requirement (Data Localization):** Article 13 mandates that health data originating within the UAE must be stored, processed, and maintained within the territory of the UAE, and cannot be transferred outside the UAE without explicit authorization from the health authority.
- **GENOVEX Status:**
  - *Current State:* Development and testing executed locally in offline sandbox mode.
  - *Gap to Production:* The production deployment (Phase 17) MUST be hosted on certified UAE in-country cloud infrastructure (e.g. Microsoft Azure UAE Central/North in Abu Dhabi/Dubai, AWS Middle East UAE Region, or local sovereign cloud providers such as Moro Hub / G42 Cloud). Cross-border telemetry egress (including unmasked external LLM APIs) is prohibited.

### 2.2 Federal Decree-Law No. 45 of 2021 on Personal Data Protection (UAE PDPL)
- **Scope:** Comprehensive data protection regime governing the processing of personal data across the UAE.
- **Key Requirements:**
  - Explicit consent for processing sensitive personal data (health and biometric data).
  - Purpose limitation and data minimization.
  - Data subject rights: Right to access, right to rectification, right to erasure, and right to restriction of processing.
- **GENOVEX Status:**
  - *Implemented:* Implemented `/api/v1/auth/privacy/export-data` (Right to Access) and `/api/v1/auth/privacy/delete-account` (Right to Erasure / Anonymization).
  - *Implemented:* Explicit pre-assessment consent capture on the frontend interface (`/assessment`).
  - *Gap to Production:* Appointment of a formally registered Data Protection Officer (DPO) and submission of cross-border data processing notifications to the UAE Data Office upon official establishment.

### 2.3 Department of Health Abu Dhabi (DoH) — ADHICS Standards
- **Scope:** Abu Dhabi Healthcare Information and Cyber Security Standard (ADHICS).
- **Key Requirements:**
  - Mandatory audit trails for all access to clinical records.
  - Robust role-based access control (RBAC).
  - Encryption in transit (TLS 1.3) and at rest (AES-256).
  - Separation of development, testing, and production environments.
- **GENOVEX Status:**
  - *Implemented:* Comprehensive immutable `AuditLog` table capturing actor, action, resource, IP, and timestamp.
  - *Implemented:* Defensive RBAC separating `PATIENT`, `CLINICIAN`, `ADMIN`, and `SUPERADMIN`.
  - *Gap to Production:* Completion of formal third-party ADHICS audit and penetration testing certification before connecting to Abu Dhabi health networks (Malaffi).

### 2.4 Dubai Health Authority (DHA) — NABIDH Health Information Exchange
- **Scope:** Dubai health data integration and security guidelines.
- **Key Requirements:** Patient consent management, HL7/FHIR compatibility for clinical reports, and licensed clinician validation.
- **GENOVEX Status:**
  - *Implemented:* Clinical reports store codified standardized outputs (`questionnaire_version_tag`, `rule_engine_version`, `outcome_tier`).
  - *Gap to Production:* FHIR R4 resource conversion layer required if future versions integrate directly into DHA NABIDH electronic medical records.

---

## 3. Software as a Medical Device (SaMD) Classification Analysis

A critical regulatory consideration for digital health applications is whether the platform constitutes **Software as a Medical Device (SaMD)** under International Medical Device Regulators Forum (IMDRF) and MOHAP guidelines:

### 3.1 Intended Use & Current Boundary Definition
GENOVEX is architected as an **evidence-linked clinical decision support (CDS) and health navigation tool**, not an autonomous diagnostic medical device:

```
[ Traditional Diagnostic SaMD ]
  Autonomous Diagnosis -> Prescriptive Treatment -> Direct Patient Management
  (Requires Class IIa/IIb/III Medical Device Clearance)

VS.

[ GENOVEX Architecture (Clinical Decision Support & Navigation) ]
  Risk Factor Identification -> Educational Stratification -> In-Person Clinical Navigation
  (Centralized Withholding Gate: Requires In-Person Clinician Physical Exam & Lab Tests)
```

### 3.2 Non-Diagnostic Safety Guardrails Enforced in Software
1. **Centralized Clinical Governance Gate:**
   Patient reports are withheld behind HTTP 422 whenever clinical rules are unapproved, preventing unvalidated software outputs from reaching patients.
2. **Deterministic Codification (Zero Hallucination):**
   Scoring and risk stratification rely exclusively on deterministic rules codified from published clinical guidelines (EAU, AUA/ASRM, WHO), not generative AI guesswork.
3. **Emergency Red Flag Hard-Stop:**
   Acute symptoms (testicular pain or palpable lumps) bypass algorithmic risk scoring and immediately direct patients to 24/7 in-person emergency hospital care.
4. **Mandatory Non-Diagnostic Disclaimers:**
   Every report, navigation page, and API response explicitly declares that the platform does NOT provide medical diagnosis or replace laboratory semen analysis.

### 3.3 Regulatory Classification & Clearance Path
If MOHAP or DHA classifies GENOVEX as a Class I or Class IIa Software as a Medical Device (SaMD) based on clinical risk assessment:
- **Prerequisite Steps Required:**
  1. Formal clinical validation study on synthetic and retrospective cohorts (documented in Phase 16).
  2. Multi-specialist clinical review board sign-off on the 22 deterministic clinical rules.
  3. Quality Management System (QMS) compliant with ISO 13485 (Medical devices — Quality management systems) and IEC 62304 (Medical device software — Software lifecycle processes).
  4. Clinical Evaluation Report (CER) compliant with MEDDEV 2.7/1 rev. 4 guidelines.

---

## 4. Comprehensive Compliance Gap Matrix

| Regulatory Requirement | Applicable Standard | Current Software Status | Gap to Commercial Launch | Action Required |
| :--- | :--- | :---: | :---: | :--- |
| **In-Country UAE Data Storage** | ICT Health Law Art. 13 | Local Sandbox | Cloud hosting location | Deploy to Microsoft Azure UAE Central or AWS Middle East (UAE) in Phase 17. |
| **Data Subject Right to Access** | UAE PDPL Art. 14 | IMPLEMENTED | None (API ready) | Operationalize customer support response workflow. |
| **Data Subject Right to Erasure** | UAE PDPL Art. 16 | IMPLEMENTED | None (API ready) | Audit automated deletion cron jobs. |
| **Clinical Rule Validation** | Clinical Governance | UNAPPROVED (22 Rules) | Clinical board review | Conclude independent clinical review board evaluation. |
| **Audit Trail Observability** | ADHICS 8.1 / DHA | IMPLEMENTED | Log retention policy | Configure 5-year immutable WORM cloud storage for audit logs. |
| **Third-Party Pen Testing** | ADHICS 10.3 | Ready for Audit | Independent test report | Retain CREST-accredited penetration testing firm. |
| **Medical Device Clearance** | MOHAP Medical Device Reg | Pre-Clearance CDS | Formal classification | Submit formal inquiry to UAE MOHAP Medical Device Registration Committee. |

---

## 5. Conclusion & Recommendations

The technical foundation of GENOVEX demonstrates exceptional compliance readiness, with data minimization, privacy workflows, encryption, and clinical safety controls natively integrated into the codebase. 

Prior to commercial or public clinical launch:
1. Ensure cloud infrastructure is deployed strictly within UAE sovereign boundaries.
2. Maintain the clinical governance gate until formal clinical sign-off is achieved.
3. Retain specialized UAE healthcare legal counsel to review terms of service and regulatory notifications.
