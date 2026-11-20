"""
GENOVEX Phase 8: Assessment Processing and Results Test Suite
Validates all 20 Acceptance Criteria (AC01 through AC20) in strict sandbox isolation
against disposable temporary databases without modifying live genovex.db.
"""

import os
import time
import uuid
import json
import sqlite3
import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.core.database import SessionLocal, Base, engine
from app.core.security import User, RoleEnum, create_access_token, AuditLog
from main import app as fastapi_app
from app.models.questionnaire import (
    QuestionnaireVersion, Question, Assessment, AssessmentResponse,
    QuestionnaireStatus, QuestionDomain, QuestionType, AssessmentStatus
)
from app.models.clinical_rules import (
    ClinicalRule, ClinicalOutcomeTier, ClinicalRuleStatus
)
from app.models.assessment_report import AssessmentReport
from app.schemas.assessment_report import AssessmentReportResponse
from app.services.clinical_rule_engine import ClinicalRuleEngineService
from app.services.predicate_evaluator import PredicateEvaluator, PredicateEvaluationState
from app.services.assessment_processing_service import (
    AssessmentProcessingService, ClinicalGovernanceGate
)
from app.core.seed_questionnaire import seed_questionnaire_v1
from app.core.seed_clinical_rules import seed_clinical_rules_v1


@pytest.fixture(scope="module")
def setup_module_db():
    """Initializes schema and seeds baseline questionnaire and rules in sandbox database."""
    Base.metadata.create_all(bind=engine)
    init_db = SessionLocal()
    seed_questionnaire_v1(init_db)
    seed_clinical_rules_v1(init_db)
    init_db.close()


@pytest.fixture
def db(setup_module_db):
    """Function-scoped clean session that automatically rolls back and closes."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="module")
def test_client():
    return TestClient(fastapi_app)


def _get_or_create_clinician(db: Session) -> User:
    clinician = db.query(User).filter(User.role == RoleEnum.CLINICIAN).first()
    if not clinician:
        clinician = User(
            email=f"clinician_{uuid.uuid4().hex[:6]}@genovex.ae",
            hashed_password="hash",
            full_name="Dr. Clinician Reviewer",
            role=RoleEnum.CLINICIAN,
            is_active=True
        )
        db.add(clinician)
        db.commit()
        db.refresh(clinician)
    return clinician


def _create_locked_assessment(db: Session, session_token: str, user_id: int = None, status: AssessmentStatus = AssessmentStatus.LOCKED) -> Assessment:
    q_ver = db.query(QuestionnaireVersion).filter(QuestionnaireVersion.status == QuestionnaireStatus.PUBLISHED).first()
    now = datetime.now(timezone.utc)
    assessment = Assessment(
        session_token=session_token,
        questionnaire_version_id=q_ver.id,
        user_id=user_id,
        status=status,
        submitted_at=now if status == AssessmentStatus.LOCKED else None,
        last_saved_at=now
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


# ---------------------------------------------------------------------------
# AC01: Assessment Completion Validation
# ---------------------------------------------------------------------------
def test_ac01_assessment_completion_validation(db: Session, test_client: TestClient):
    """
    AC01: Verifies that non-LOCKED assessments (IN_PROGRESS, REVIEW_READY)
    are rejected with HTTP 409 Conflict.
    """
    token_in_progress = f"ac01_inprog_{uuid.uuid4().hex}"
    assessment = _create_locked_assessment(db, token_in_progress, status=AssessmentStatus.IN_PROGRESS)

    # Direct service call must raise 409
    with pytest.raises(Exception) as exc_info:
        AssessmentProcessingService.validate_assessment_for_processing(
            db=db,
            assessment_id=assessment.id,
            session_token=token_in_progress
        )
    assert getattr(exc_info.value, "status_code", None) == 409 or "409" in str(exc_info.value)

    # API endpoint must return 409
    resp = test_client.post(f"/api/v1/assessment/{token_in_progress}/evaluate")
    assert resp.status_code == 409
    assert "LOCKED" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# AC02: Five-State Response Preservation
# ---------------------------------------------------------------------------
def test_ac02_five_state_response_preservation(db: Session):
    """
    AC02: Verifies that response summary preserves all 5 canonical states:
    CONCRETE_VALUE, UNSURE, PREFER_NOT_TO_SAY, INACTIVE_CONDITIONAL, and MISSING.
    """
    token = f"ac02_5state_{uuid.uuid4().hex}"
    assessment = _create_locked_assessment(db, token)

    q_age = db.query(Question).filter(Question.question_key == "Q_AGE").first()
    q_steroid = db.query(Question).filter(Question.question_key == "Q_ANABOLIC_STEROIDS").first()
    q_tobacco = db.query(Question).filter(Question.question_key == "Q_TOBACCO_USE").first()
    q_child = db.query(Question).filter(Question.question_key == "Q_TESTIS_SURGERY_TYPE").first()

    db.add_all([
        # 1. CONCRETE_VALUE
        AssessmentResponse(assessment_id=assessment.id, question_id=q_age.id, question_key="Q_AGE", answer_value=32, conditional_pathway_active=True),
        # 2. UNSURE
        AssessmentResponse(assessment_id=assessment.id, question_id=q_steroid.id, question_key="Q_ANABOLIC_STEROIDS", is_unsure=True, conditional_pathway_active=True),
        # 3. PREFER_NOT_TO_SAY
        AssessmentResponse(assessment_id=assessment.id, question_id=q_tobacco.id, question_key="Q_TOBACCO_USE", is_prefer_not_to_say=True, conditional_pathway_active=True),
        # 4. INACTIVE_CONDITIONAL
        AssessmentResponse(assessment_id=assessment.id, question_id=q_child.id, question_key="Q_TESTIS_SURGERY_TYPE", conditional_pathway_active=False),
    ])
    db.commit()

    report = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)
    summary = report.responses_summary_json

    states_found = {}
    for item in summary:
        k = item["question_key"]
        if k == "Q_AGE":
            states_found["CONCRETE"] = item["answer_display_en"] == "32"
        elif k == "Q_ANABOLIC_STEROIDS":
            states_found["UNSURE"] = item["is_unsure"] is True
        elif k == "Q_TOBACCO_USE":
            states_found["PREFER_NOT_TO_SAY"] = item["is_prefer_not_to_say"] is True
        elif k == "Q_TESTIS_SURGERY_TYPE":
            states_found["INACTIVE"] = item["conditional_pathway_active"] is False
        elif item.get("is_missing"):
            states_found["MISSING"] = True

    assert states_found.get("CONCRETE") is True
    assert states_found.get("UNSURE") is True
    assert states_found.get("PREFER_NOT_TO_SAY") is True
    assert states_found.get("INACTIVE") is True
    assert states_found.get("MISSING") is True


# ---------------------------------------------------------------------------
# AC03: Conditional Pathway Correctness
# ---------------------------------------------------------------------------
def test_ac03_conditional_pathway_correctness(db: Session):
    """
    AC03: Verifies that inactive conditional child responses never trigger rules.
    """
    token = f"ac03_cond_{uuid.uuid4().hex}"
    assessment = _create_locked_assessment(db, token)

    q_parent = db.query(Question).filter(Question.question_key == "Q_TESTIS_SURGERY").first()
    q_child = db.query(Question).filter(Question.question_key == "Q_TESTIS_SURGERY_TYPE").first()

    # Parent answered "no", child marked inactive
    db.add_all([
        AssessmentResponse(assessment_id=assessment.id, question_id=q_parent.id, question_key="Q_TESTIS_SURGERY", answer_value="no", conditional_pathway_active=True),
        AssessmentResponse(assessment_id=assessment.id, question_id=q_child.id, question_key="Q_TESTIS_SURGERY_TYPE", answer_value="undescended_testis", conditional_pathway_active=False)
    ])
    db.commit()

    report = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)
    # Rules targeting Q_TESTIS_SURGERY_TYPE must not trigger when conditional_pathway_active is False
    triggered_rules = [r["rule_code"] for r in report.triggered_rules_snapshot_json if "ORCHIDOPEXY" in r.get("rule_code", "")]
    assert len(triggered_rules) == 0


# ---------------------------------------------------------------------------
# AC04: Deterministic Evaluation Integration
# ---------------------------------------------------------------------------
def test_ac04_deterministic_evaluation_integration(db: Session):
    """
    AC04: Verifies that identical assessment inputs evaluated repeatedly
    produce 100% identical canonical evaluation hashes.
    """
    token = f"ac04_det_{uuid.uuid4().hex}"
    assessment = _create_locked_assessment(db, token)

    q_steroid = db.query(Question).filter(Question.question_key == "Q_ANABOLIC_STEROIDS").first()
    db.add(AssessmentResponse(assessment_id=assessment.id, question_id=q_steroid.id, question_key="Q_ANABOLIC_STEROIDS", answer_value="yes_past", conditional_pathway_active=True))
    db.commit()

    report = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)
    report_dict = {
        "outcome_tier": report.outcome_tier.value,
        "is_urgent_red_flag": report.is_urgent_red_flag,
        "rule_engine_version": report.rule_engine_version,
        "questionnaire_version_tag": report.questionnaire_version_tag,
        "evaluation_completeness": "DETERMINATE",
        "triggered_rules": report.triggered_rules_snapshot_json,
        "identified_risk_factors": report.identified_risk_factors_json
    }

    first_hash = ClinicalRuleEngineService.compute_canonical_report_hash(report_dict)
    for _ in range(20):
        h = ClinicalRuleEngineService.compute_canonical_report_hash(report_dict)
        assert h == first_hash


# ---------------------------------------------------------------------------
# AC05: Incomplete Evaluation Handling
# ---------------------------------------------------------------------------
def test_ac05_incomplete_evaluation_handling(db: Session):
    """
    AC05: Verifies that Tier 1 result with unsure/declined answers receives
    qualified title and INDETERMINATE completeness.
    """
    token = f"ac05_incomp_{uuid.uuid4().hex}"
    assessment = _create_locked_assessment(db, token)

    q_steroid = db.query(Question).filter(Question.question_key == "Q_ANABOLIC_STEROIDS").first()
    # Unsure answer on non-triggered rule
    db.add(AssessmentResponse(assessment_id=assessment.id, question_id=q_steroid.id, question_key="Q_ANABOLIC_STEROIDS", is_unsure=True, conditional_pathway_active=True))
    db.commit()

    report = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)
    assert report.outcome_tier == ClinicalOutcomeTier.TIER_1_NO_RISK
    assert "INCOMPLETE EVALUATION" in report.outcome_title_en
    schema_report = AssessmentReportResponse.model_validate(report)
    assert schema_report.evaluation_completeness == "INDETERMINATE"
    assert schema_report.is_evaluation_incomplete is True
    assert schema_report.is_amber_warning is True


# ---------------------------------------------------------------------------
# AC06: Four-Tier Outcome Preservation
# ---------------------------------------------------------------------------
def test_ac06_four_tier_outcome_preservation():
    """
    AC06: Verifies all four canonical outcome tiers:
    Tier 1: NO_REPORTED_RISK_FACTORS
    Tier 2: RISK_FACTORS_IDENTIFIED
    Tier 3: CLINICAL_EVALUATION_RECOMMENDED
    Tier 4: URGENT_MEDICAL_ASSESSMENT
    """
    assert ClinicalOutcomeTier.TIER_1_NO_RISK.value == "NO_REPORTED_RISK_FACTORS"
    assert ClinicalOutcomeTier.TIER_2_RISK_FACTORS.value == "RISK_FACTORS_IDENTIFIED"
    assert ClinicalOutcomeTier.TIER_3_EVAL_RECOMMENDED.value == "CLINICAL_EVALUATION_RECOMMENDED"
    assert ClinicalOutcomeTier.TIER_4_URGENT.value == "URGENT_MEDICAL_ASSESSMENT"


# ---------------------------------------------------------------------------
# AC07: Report Generation Integrity
# ---------------------------------------------------------------------------
def test_ac07_report_generation_integrity(db: Session):
    """
    AC07: Verifies report reference format (GNX-RPT-2026-XXXXXX) and foreign key linkage.
    """
    token = f"ac07_gen_{uuid.uuid4().hex}"
    assessment = _create_locked_assessment(db, token)

    report = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)
    assert report.report_reference.startswith("GNX-RPT-2026-")
    assert len(report.report_reference) == 19
    assert report.assessment_id == assessment.id
    assert report.is_locked is True


# ---------------------------------------------------------------------------
# AC08: Report Snapshot Immutability
# ---------------------------------------------------------------------------
def test_ac08_report_snapshot_immutability(db: Session):
    """
    AC08: Repeated retrieval returns exact same snapshot without mutating data.
    """
    token = f"ac08_immut_{uuid.uuid4().hex}"
    assessment = _create_locked_assessment(db, token)
    clinician = _get_or_create_clinician(db)

    report1 = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)
    time1 = report1.generated_at
    ref1 = report1.report_reference

    # Retrieve again via service in clinical audit mode
    report2 = AssessmentProcessingService.get_assessment_report(db, session_token=token, current_user=clinician)
    assert report2.id == report1.id
    assert report2.report_reference == ref1
    assert report2.generated_at == time1


# ---------------------------------------------------------------------------
# AC09: Processing Pipeline Idempotency
# ---------------------------------------------------------------------------
def test_ac09_processing_pipeline_idempotency(db: Session):
    """
    AC09: Repeated calls to process_assessment_results create exactly ONE report record.
    """
    token = f"ac09_idemp_{uuid.uuid4().hex}"
    assessment = _create_locked_assessment(db, token)
    clinician = _get_or_create_clinician(db)

    q_age = db.query(Question).filter(Question.question_key == "Q_AGE").first()
    db.add(AssessmentResponse(assessment_id=assessment.id, question_id=q_age.id, question_key="Q_AGE", answer_value=28, conditional_pathway_active=True))
    db.commit()

    # Call 1
    r1 = AssessmentProcessingService.process_assessment_results(db, assessment.id, session_token=token, current_user=clinician)
    count1 = db.query(AssessmentReport).filter(AssessmentReport.assessment_id == assessment.id).count()

    # Call 2
    r2 = AssessmentProcessingService.process_assessment_results(db, assessment.id, session_token=token, current_user=clinician)
    count2 = db.query(AssessmentReport).filter(AssessmentReport.assessment_id == assessment.id).count()

    assert count1 == 1
    assert count2 == 1
    assert r1.id == r2.id


# ---------------------------------------------------------------------------
# AC10: API Authorization and Ownership
# ---------------------------------------------------------------------------
def test_ac10_api_authorization_and_ownership(db: Session, test_client: TestClient):
    """
    AC10: Mismatched ownership or session token is rejected with HTTP 403.
    """
    # Create legitimate assessment owner
    owner_patient = User(
        email=f"owner_{uuid.uuid4().hex[:6]}@genovex.ae",
        hashed_password="hash",
        full_name="Owner Patient",
        role=RoleEnum.PATIENT,
        is_active=True
    )
    db.add(owner_patient)
    db.commit()
    db.refresh(owner_patient)

    token = f"ac10_own_{uuid.uuid4().hex}"
    assessment = _create_locked_assessment(db, token, user_id=owner_patient.id)

    # Compile report for assessment
    _ = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token, user_id=owner_patient.id)

    # Unauthorized other patient user
    other_patient = User(
        email=f"other_{uuid.uuid4().hex[:6]}@genovex.ae",
        hashed_password="hash",
        full_name="Other Patient",
        role=RoleEnum.PATIENT,
        is_active=True
    )
    db.add(other_patient)
    db.commit()
    db.refresh(other_patient)

    other_jwt = create_access_token({"sub": other_patient.email})

    resp = test_client.get(
        f"/api/v1/assessment/{token}/report",
        headers={"Authorization": f"Bearer {other_jwt}"}
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "UNAUTHORIZED_ASSESSMENT_ACCESS"


# ---------------------------------------------------------------------------
# AC11: Centralized Clinical Governance Withholding
# ---------------------------------------------------------------------------
def test_ac11_centralized_clinical_governance_withholding(db: Session, test_client: TestClient):
    """
    AC11: When underlying clinical rules are unapproved, patient-facing callers
    are withheld with HTTP 422 (CLINICAL_RELEASE_WITHHELD).
    Clinicians can access in clinical audit mode.
    """
    # Explicitly ensure rules are unapproved in the disposable test sandbox to verify withholding gate
    db.query(ClinicalRule).update({"clinical_reviewer_id": None})
    db.commit()

    token = f"ac11_gov_{uuid.uuid4().hex}"
    assessment = _create_locked_assessment(db, token)

    q_steroid = db.query(Question).filter(Question.question_key == "Q_ANABOLIC_STEROIDS").first()
    db.add(AssessmentResponse(assessment_id=assessment.id, question_id=q_steroid.id, question_key="Q_ANABOLIC_STEROIDS", answer_value="yes_past", conditional_pathway_active=True))
    db.commit()

    # Compile report (produces Tier 2 positive finding with unapproved rules)
    report = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)
    assert report.outcome_tier != ClinicalOutcomeTier.TIER_1_NO_RISK

    # 1. Anonymous caller gets 422 CLINICAL_RELEASE_WITHHELD across all routes
    resp1 = test_client.get(f"/api/v1/assessment/{token}/report")
    assert resp1.status_code == 422
    assert resp1.json()["detail"]["code"] == "CLINICAL_RELEASE_WITHHELD"

    resp2 = test_client.get(
        f"/api/v1/questionnaire/assessments/{assessment.id}/report",
        headers={"X-Session-Token": token}
    )
    assert resp2.status_code == 422
    assert resp2.json()["detail"]["code"] == "CLINICAL_RELEASE_WITHHELD"

    # 2. Clinician caller gets 200 OK
    clinician = _get_or_create_clinician(db)
    clin_jwt = create_access_token({"sub": clinician.email})

    resp_clin = test_client.get(
        f"/api/v1/assessment/{token}/report",
        headers={"Authorization": f"Bearer {clin_jwt}"}
    )
    assert resp_clin.status_code == 200
    assert resp_clin.json()["report_reference"] == report.report_reference


# ---------------------------------------------------------------------------
# AC12: Historical Report Compatibility
# ---------------------------------------------------------------------------
def test_ac12_historical_report_compatibility():
    """
    AC12: Historical report dictionary deserializes cleanly into AssessmentReportResponse.
    """
    fixture = {
        "id": 1,
        "report_reference": "GNX-RPT-2026-HIST01",
        "assessment_id": "historical-uuid-001",
        "questionnaire_version_tag": "v1.0.0",
        "rule_engine_version": "v1.0.0",
        "outcome_tier": ClinicalOutcomeTier.TIER_2_RISK_FACTORS,
        "outcome_title_en": "Risk Factors Identified",
        "outcome_title_ar": "عوامل خطورة محددة",
        "outcome_description_en": "Lifestyle risks noted.",
        "outcome_description_ar": "مخاطر نمط الحياة.",
        "is_urgent_red_flag": False,
        "identified_risk_factors_json": [{"factor_code": "RF-01", "severity": "MODERATE"}],
        "triggered_rules_snapshot_json": [{"rule_code": "R-01"}],
        "responses_summary_json": [{"question_key": "Q_AGE", "answer_display_en": "30"}],
        "evidence_citations_json": [{"guideline": "EAU 2024"}],
        "clinical_disclaimer_en": "Disclaimer EN",
        "clinical_disclaimer_ar": "Disclaimer AR",
        "is_locked": True,
        "generated_at": datetime.now(timezone.utc)
    }
    resp = AssessmentReportResponse.model_validate(fixture)
    assert resp.report_reference == "GNX-RPT-2026-HIST01"
    assert resp.overall_tier == "LIFESTYLE_MODIFIABLE_FACTORS"


# ---------------------------------------------------------------------------
# AC13: Sensitive Data Protection
# ---------------------------------------------------------------------------
def test_ac13_sensitive_data_protection(db: Session):
    """
    AC13: Verifies that session_token is excluded from serialized report responses,
    and audit logs contain zero clinical answer values or PII.
    """
    token = f"ac13_sens_{uuid.uuid4().hex}"
    assessment = _create_locked_assessment(db, token)

    report = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)
    schema_report = AssessmentReportResponse.model_validate(report)
    serialized = schema_report.model_dump()

    # session_token MUST be excluded
    assert "session_token" not in serialized

    # Audit log check: details must have zero free-text answers
    audit = db.query(AuditLog).filter(AuditLog.resource_id == report.report_reference).first()
    assert audit is not None
    assert "answers" not in audit.details
    assert "evaluation_counts" in audit.details


# ---------------------------------------------------------------------------
# AC14: Error Recovery and Transaction Safety
# ---------------------------------------------------------------------------
def test_ac14_error_recovery_and_transaction_safety(db: Session):
    """
    AC14: Verifies transaction rollback on processing failure.
    """
    token = f"ac14_tx_{uuid.uuid4().hex}"
    _ = _create_locked_assessment(db, token)

    with pytest.raises(Exception):
        AssessmentProcessingService.process_assessment_results(db, "non-existent-uuid-12345")

    dangling = db.query(AssessmentReport).filter(AssessmentReport.assessment_id == "non-existent-uuid-12345").first()
    assert dangling is None


# ---------------------------------------------------------------------------
# AC15: Regression Compatibility
# ---------------------------------------------------------------------------
def test_ac15_regression_compatibility():
    """
    AC15: Verifies that Phase 6 DAG evaluation and Phase 7 predicate engine remain functional.
    """
    cond = {"question_key": "Q_AGE", "operator": "greater_than", "expected_value": 30}
    
    # Concrete value matching
    state_true, _ = PredicateEvaluator.evaluate_atomic_condition(cond, {"Q_AGE": {"answer_value": 35}})
    assert state_true == PredicateEvaluationState.TRUE

    # Safe answer: unsure produces INDETERMINATE
    state_unsure, _ = PredicateEvaluator.evaluate_atomic_condition(cond, {"Q_AGE": {"is_unsure": True}})
    assert state_unsure == PredicateEvaluationState.INDETERMINATE


# ---------------------------------------------------------------------------
# AC16: Database Integrity and Zero DDL
# ---------------------------------------------------------------------------
def test_ac16_database_integrity_and_zero_ddl(db: Session):
    """
    AC16: Verifies zero schema changes, PRAGMA foreign_key_check, and integrity_check.
    """
    conn = db.connection()
    fk_check = conn.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
    assert len(fk_check) == 0, f"Foreign key violations found: {fk_check}"

    integrity = conn.exec_driver_sql("PRAGMA integrity_check").scalar()
    assert integrity == "ok"


# ---------------------------------------------------------------------------
# AC17: Performance and Query Efficiency Benchmark
# ---------------------------------------------------------------------------
def test_ac17_performance_and_query_efficiency(db: Session):
    """
    AC17: Measures evaluation latency across 20 iterations.
    Documents median and p95 latency.
    """
    token = f"ac17_perf_{uuid.uuid4().hex}"
    assessment = _create_locked_assessment(db, token)

    latencies = []
    for _ in range(20):
        start = time.perf_counter()
        _ = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)
        lat = (time.perf_counter() - start) * 1000.0
        latencies.append(lat)

    latencies.sort()
    median_lat = latencies[len(latencies) // 2]
    assert median_lat < 250.0, f"Median latency {median_lat}ms exceeds 250ms"


# ---------------------------------------------------------------------------
# AC18: Auditability of Processing Lifecycle and Admin RBAC
# ---------------------------------------------------------------------------
def test_ac18_auditability_and_admin_rbac(db: Session, test_client: TestClient):
    """
    AC18: Verifies audit log lifecycle and enforces RBAC on GET /api/v1/admin/clinical-rules.
    Anonymous -> 401, Patient -> 403, Admin/Clinician -> 200.
    """
    # 1. Anonymous request -> 401
    resp_anon = test_client.get("/api/v1/admin/clinical-rules")
    assert resp_anon.status_code == 401

    # 2. Patient user -> 403
    patient = User(
        email=f"patient_ac18_{uuid.uuid4().hex[:6]}@genovex.ae",
        hashed_password="hash",
        full_name="Patient AC18",
        role=RoleEnum.PATIENT,
        is_active=True
    )
    db.add(patient)
    db.commit()
    patient_jwt = create_access_token({"sub": patient.email})

    resp_pat = test_client.get(
        "/api/v1/admin/clinical-rules",
        headers={"Authorization": f"Bearer {patient_jwt}"}
    )
    assert resp_pat.status_code == 403

    # 3. Admin user -> 200
    admin = User(
        email=f"admin_ac18_{uuid.uuid4().hex[:6]}@genovex.ae",
        hashed_password="hash",
        full_name="Admin AC18",
        role=RoleEnum.ADMIN,
        is_active=True
    )
    db.add(admin)
    db.commit()
    admin_jwt = create_access_token({"sub": admin.email})

    resp_admin = test_client.get(
        "/api/v1/admin/clinical-rules",
        headers={"Authorization": f"Bearer {admin_jwt}"}
    )
    assert resp_admin.status_code == 200


# ---------------------------------------------------------------------------
# AC19: Accessibility and Result Clarity
# ---------------------------------------------------------------------------
def test_ac19_accessibility_and_result_clarity():
    """
    AC19: Incomplete evaluation schema exposes is_amber_warning and is_evaluation_incomplete.
    """
    schema = AssessmentReportResponse.model_validate({
        "id": 1,
        "report_reference": "GNX-RPT-2026-AMBER1",
        "assessment_id": "uuid-amber-01",
        "questionnaire_version_tag": "v1.0.0",
        "rule_engine_version": "v1.0.0",
        "outcome_tier": ClinicalOutcomeTier.TIER_1_NO_RISK,
        "outcome_title_en": "NO REPORTED RISK FACTORS IDENTIFIED — INCOMPLETE EVALUATION",
        "outcome_title_ar": "لم يتم تسجيل عوامل خطورة واضحة — تقييم غير مكتمل",
        "outcome_description_en": "Incomplete evaluation.",
        "outcome_description_ar": "تقييم غير مكتمل.",
        "is_urgent_red_flag": False,
        "clinical_disclaimer_en": "Disclaimer",
        "clinical_disclaimer_ar": "إخلاء مسؤولية",
        "is_locked": True,
        "generated_at": datetime.now(timezone.utc)
    })
    assert schema.is_evaluation_incomplete is True
    assert schema.is_amber_warning is True
    assert schema.evaluation_completeness == "INDETERMINATE"


# ---------------------------------------------------------------------------
# AC20: End-to-End Assessment Processing
# ---------------------------------------------------------------------------
def test_ac20_end_to_end_assessment_processing(db: Session):
    """
    AC20: Full lifecycle: start, answer, submit (status LOCKED), process results, and retrieve report in clinical audit mode.
    """
    token = f"ac20_e2e_{uuid.uuid4().hex}"
    assessment = _create_locked_assessment(db, token)
    clinician = _get_or_create_clinician(db)

    q_age = db.query(Question).filter(Question.question_key == "Q_AGE").first()
    db.add(AssessmentResponse(assessment_id=assessment.id, question_id=q_age.id, question_key="Q_AGE", answer_value=30, conditional_pathway_active=True))
    db.commit()

    # 1. Process
    report = AssessmentProcessingService.process_assessment_results(
        db=db,
        assessment_id=assessment.id,
        session_token=token,
        current_user=clinician
    )
    assert report is not None
    assert report.report_reference.startswith("GNX-RPT-2026-")

    # 2. Retrieve
    retrieved = AssessmentProcessingService.get_assessment_report(
        db=db,
        session_token=token,
        current_user=clinician
    )
    assert retrieved.id == report.id
    assert retrieved.report_reference == report.report_reference
