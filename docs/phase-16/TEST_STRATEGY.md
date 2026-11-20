# GENOVEX: TEST STRATEGY & QUALITY ASSURANCE SPECIFICATION
## Multi-Tier Quality Engineering Framework for Reproductive Digital Health

**Project:** GENOVEX – Male Reproductive Health Risk Identification & Clinical Navigation Platform  
**Roadmap Phase:** Phase 16 – Testing & Validation  
**Date:** 20 November 2026  
**QA Lead:** Lead Software Quality Assurance Engineer & Clinical Safety Lead  
**Scope:** Unit, Integration, Adversarial Security, Clinical Governance, End-to-End & Performance Testing

---

## 1. Quality Engineering Philosophy & Objectives

The GENOVEX platform operates at the critical intersection of digital health, clinical risk stratification, and patient navigation. The QA strategy is guided by three non-negotiable principles:
1. **Clinical Safety First (Zero False Reassurance):** Incomplete evaluations or ambiguous answers must never generate a falsely reassuring Tier 1 outcome. Urgent symptoms must hard-stop into emergency guidance.
2. **Authoritative Database Inviolability:** The authoritative production database (`genovex.db`) must remain permanently unmutated during test execution. 100% of test runs must execute against dynamically provisioned, isolated disposable sandboxes.
3. **Deterministic Reproducibility:** Given identical inputs, questionnaire DAG branching, clinical rule evaluation, and report snapshot compilation must yield 100% bit-for-bit identical outputs across environments.

---

## 2. Multi-Tier Testing Pyramid

```
                ▲
               / \
              /   \
             / E2E \       Frontend Integration & User Journeys (Vitest + JSDOM)
            /-------\
           / Service \     Clinical Rule Engine, AI Sandboxing & PDF Compilation
          /-----------\
         / Integration \   REST APIs, RBAC, IDOR, Session & Database Invariants
        /---------------\
       /      Unit       \ Mathematical Predicates, DAG Validation, Hashing, Types
      /-------------------\
```

### 2.1 Backend Testing Framework (Pytest 9.1+)
- **Runner:** `pytest` with `pytest-asyncio` and HTTPX `TestClient`.
- **Database Sandbox Redirection:** `conftest.py` copies `genovex.db` to a temporary directory on startup and rebinds SQLAlchemy `engine` and `SessionLocal`. An automated adversarial safety fixture aborts execution if any connection points to the authoritative path.
- **Coverage Areas:**
  - Questionnaire topological DAG ordering and cycle rejection (`test_phase6_adaptive_engine.py`).
  - Deterministic clinical rule predicate evaluation (`test_phase7_clinical_rule_engine.py`).
  - Five-state response protocol and report compilation (`test_phase8_assessment_processing.py`).
  - Sandboxed Gemini AI integration and clinician review portal (`test_phase9_10_ai_and_clinician.py`).
  - Admin dashboard, operational telemetry, and user management (`test_phase11_admin_dashboard.py`).
  - Clinical navigation, provider directory, and specialty routing (`test_phase12_clinical_navigation.py`).
  - Assessment history, report snapshots, and bilingual PDF generation (`test_phase13_reports_and_history.py`).
  - Database schema parity, account management, and profile APIs (`test_phase14_database_and_api.py`).
  - Privacy workflows, data erasure, and PBKDF2 hashing security (`test_phase15_security_and_privacy.py`).
  - Centralized clinical governance withholding gate (`test_clinical_governance_adversarial.py`).
  - Database sandbox isolation and read-only fail-safes (`test_database_isolation_adversarial.py`).

### 2.2 Frontend Testing Framework (Vitest 2.1+)
- **Runner:** `vitest` with `@testing-library/react` and `jsdom`.
- **Component & Workflow Coverage:**
  - Questionnaire navigation, question answer selection, and pre-submission validation (`questionnaire.test.tsx`).
  - Clinician portal queue rendering and note authoring (`clinician_and_ai.test.tsx`).
  - Admin dashboard operational tabs, status modals, and telemetry cards (`admin_dashboard.test.tsx`).
  - Clinical navigation provider directory and assessment history timeline (`navigation_and_history.test.tsx`).
  - Assessment report tier rendering and emergency safety banner (`report.test.tsx`).
  - Authentication login and session management (`auth.test.tsx`).
  - API error handling, network failure resilience, and bilingual RTL layout (`api_resilience.test.tsx`, `rtl_and_navigation.test.tsx`).

---

## 3. Adversarial Security & Boundary Testing Strategy

1. **Privilege Escalation:**
   - Test unauthenticated access (401).
   - Test vertical role escalation: Patient attempting admin endpoints (403), Clinician attempting rule approval (403), Admin attempting superadmin role elevation (403).
2. **Horizontal IDOR Testing:**
   - User A querying User B's assessment report or history -> 403 / empty result.
   - User B attempting to claim User A's existing assessment -> 403 Forbidden.
3. **Denial-of-Service / Parameter Injection:**
   - Excessive pagination bounds (`limit=10000`, `page_size=5000`) -> 422 Unprocessable Content.
   - Blank / whitespace audit reasons -> 422 Unprocessable Content.
4. **Lockout Protection Invariant:**
   - Attempting to deactivate or demote the last remaining active SuperAdmin -> 400 Bad Request.

---

## 4. Synthetic Clinical Validation Strategy

To validate clinical risk stratification without exposing real patient records, testing utilizes codified synthetic patient profiles across the four clinical tiers:
- **Scenario A (Tier 4 Urgent):** 24yo male reporting sudden acute scrotal pain (onset < 2 hours) -> Must trigger Tier 4 Urgent Medical Assessment and surface 24/7 emergency hospital routing.
- **Scenario B (Tier 4 Urgent):** 31yo male reporting palpable painless testicular lump -> Must trigger Tier 4 Urgent Medical Assessment with urgent urological ultrasound recommendation.
- **Scenario C (Tier 3 Specialist):** 34yo couple attempting conception for 18 months with history of childhood bilateral cryptorchidism -> Must trigger Tier 3 Specialist Evaluation Recommended.
- **Scenario D (Tier 2 Lifestyle):** 28yo male reporting daily shisha and dokha use, sedentary job, and sauna exposure -> Must trigger Tier 2 Lifestyle & Modifiable Factors.
- **Scenario E (Tier 1 Incomplete):** Healthy 26yo answering "Unsure" to childhood surgery and "Prefer not to say" to anabolic steroid use -> Must trigger `INCOMPLETE_EVALUATION_WITHHELD` (HTTP 422) to prevent false reassurance.
