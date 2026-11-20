# GENOVEX Questionnaire Version Maintenance Specification

## 1. Adaptive Questionnaire Versioning Architecture

The GENOVEX 11-Domain Adaptive Questionnaire captures clinical risk indicators across male reproductive biology:
1. Basic Health & Demographics
2. Reproductive History
3. Testicular & Scrotal History
4. Medical & Surgical History
5. Hormonal Health
6. Metabolic Health
7. Lifestyle & Habits
8. Medication & Substance History
9. Occupational & Environmental Exposure
10. Sexual & Ejaculatory Health
11. Family & Genetic History

---

## 2. Questionnaire Version Pinning

To guarantee data integrity across ongoing user sessions:
- When a user initiates an assessment (`POST /api/v1/assessment/start`), the system looks up the currently active, published questionnaire (`QuestionnaireStatus.PUBLISHED`).
- The assessment record permanently pins the foreign key `questionnaire_version_id`.
- **Session Pinning Invariant:** All subsequent domain submissions and conditional branches for that assessment resolve questions belonging strictly to the pinned version.
- Even if an administrator publishes a new questionnaire version (`v2.0.0`) while a user is answering questions, the user's ongoing session completes without error or unexpected schema shifts.

---

## 3. Dynamic Conditional Branching Safeguards

Questions employ deterministic display logic (e.g., displaying duration questions only if anabolic steroid use is affirmed):
- Dependent questions validate parent question responses before storage.
- If a user changes a parent response (e.g., toggles from "Yes" to "No"), previously answered child questions are safely reset or omitted from clinical rule evaluation.
- The safe answer options (`"prefer_not_to_say"`, `"unsure"`) never trigger false-positive clinical alerts and are categorized cleanly as unknown/unreported.

---

## 4. Questionnaire Version Migration & Publishing Checklist

Before publishing a new questionnaire version:
1. Ensure all 11 medical domains contain appropriate questions.
2. Confirm both English and Arabic translations exist for all question prompts and answer option labels.
3. Validate that question IDs referenced in clinical rules match active question definitions.
4. Obtain formal clinical approval from a verified clinician.
5. Transition status: `DRAFT` -> `UNDER_REVIEW` -> `APPROVED` -> `PUBLISHED`.
6. Previous published version automatically transitions to `ARCHIVED`.
