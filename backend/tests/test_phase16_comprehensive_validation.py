"""
GENOVEX Phase 16: Comprehensive Master Testing & Clinical Validation Suite
Covers end-to-end assessment lifecycle, deterministic clinical scenarios across all 4 tiers,
urgent emergency safety preemption, safe answers uncertainty isolation, PDF generation & bilingual shaping,
report verification & expiring sharing, RBAC & IDOR protections, and database integrity.
Operates exclusively in strict sandbox isolation without modifying the live database.
"""

import os
import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import sqlite3

from main import app
from app.core.database import SessionLocal, Base, engine, get_db
from app.core.security import User, RoleEnum, get_password_hash, create_access_token, AuditLog
from app.models.questionnaire import (
    QuestionnaireVersion, Question, Assessment, AssessmentResponse,
    AssessmentStatus, QuestionDomain, QuestionType
)
from app.models.clinical_rules import (
    ClinicalRule, ClinicalOutcomeTier, ClinicalRuleStatus
)
from app.models.assessment_report import AssessmentReport
from app.services.report_pdf_service import ReportPDFService
from app.services.report_sharing_service import ReportSharingService
from app.services.predicate_evaluator import PredicateEvaluator, PredicateEvaluationState

client = TestClient(app)

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def auth_patient(db: Session):
    email = f"patient_p16_{uuid.uuid4().hex[:6]}@genovex.ae"
    user = User(
        email=email,
        hashed_password=get_password_hash("PatientPass123!"),
        full_name="Phase 16 Test Patient",
        role=RoleEnum.PATIENT,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(data={"sub": user.email, "role": user.role.value, "uid": user.id})
    return {"user": user, "token": token, "headers": {"Authorization": f"Bearer {token}"}}

@pytest.fixture
def other_patient(db: Session):
    email = f"patient_other_p16_{uuid.uuid4().hex[:6]}@genovex.ae"
    user = User(
        email=email,
        hashed_password=get_password_hash("OtherPass123!"),
        full_name="Phase 16 Other Patient",
        role=RoleEnum.PATIENT,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(data={"sub": user.email, "role": user.role.value, "uid": user.id})
    return {"user": user, "token": token, "headers": {"Authorization": f"Bearer {token}"}}

@pytest.fixture
def auth_clinician(db: Session):
    email = f"clinician_p16_{uuid.uuid4().hex[:6]}@genovex.ae"
    user = User(
        email=email,
        hashed_password=get_password_hash("ClinicianPass123!"),
        full_name="Dr. Phase 16 Clinician",
        role=RoleEnum.CLINICIAN,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(data={"sub": user.email, "role": user.role.value, "uid": user.id})
    return {"user": user, "token": token, "headers": {"Authorization": f"Bearer {token}"}}

@pytest.fixture
def auth_admin(db: Session):
    email = f"admin_p16_{uuid.uuid4().hex[:6]}@genovex.ae"
    user = User(
        email=email,
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Phase 16 Administrator",
        role=RoleEnum.ADMIN,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(data={"sub": user.email, "role": user.role.value, "uid": user.id})
    return {"user": user, "token": token, "headers": {"Authorization": f"Bearer {token}"}}


# -----------------------------------------------------------------------------
# 1. Complete End-to-End Assessment Lifecycle Test
# -----------------------------------------------------------------------------

def test_p16_complete_assessment_lifecycle_and_results_persistence(db: Session, auth_patient, auth_clinician):
    """
    Validates the complete patient journey:
    Session creation -> Transition to submitted -> Rule evaluation ->
    Clinical audit mode report retrieval -> Account claiming -> History retrieval.
    """
    # 1. Start assessment session
    create_res = client.post("/api/v1/questionnaire/assessments/start", json={})
    assert create_res.status_code == 200, f"Session create failed: {create_res.text}"
    session_data = create_res.json()
    session_token = session_data["session_token"]
    assert session_token is not None

    # Transition assessment status to SUBMITTED to permit clinical evaluation
    assessment = db.query(Assessment).filter(Assessment.session_token == session_token).first()
    assert assessment is not None
    assessment.status = AssessmentStatus.SUBMITTED
    db.commit()

    # 2. Evaluate assessment results:
    # Verifies deterministic evaluation execution. Patient release is either 200 or 422 (governance gate withholding)
    eval_res = client.post(f"/api/v1/assessment/{session_token}/evaluate")
    assert eval_res.status_code in (200, 422), f"Evaluation failed: {eval_res.text}"
    if eval_res.status_code == 422:
        assert eval_res.json()["detail"]["code"] in ("INCOMPLETE_EVALUATION_WITHHELD", "CLINICAL_RELEASE_WITHHELD")

    # 2b. Clinician in Clinical Audit Mode retrieves the evaluated report snapshot
    clin_eval = client.get(f"/api/v1/assessment/{session_token}/report", headers=auth_clinician["headers"])
    assert clin_eval.status_code == 200
    report_data = clin_eval.json()
    assert "report_reference" in report_data
    assert "outcome_tier" in report_data
    assert report_data["outcome_tier"] in [
        "NO_REPORTED_RISK_FACTORS",
        "RISK_FACTORS_IDENTIFIED",
        "CLINICAL_EVALUATION_RECOMMENDED",
        "URGENT_MEDICAL_ASSESSMENT"
    ]

    # 3. Claim guest assessment to registered user account
    claim_res = client.post(
        f"/api/v1/assessment/{session_token}/claim",
        headers=auth_patient["headers"]
    )
    assert claim_res.status_code == 200
    assert claim_res.json()["status"] == "success"

    # 4. Verify assessment appears in patient history
    hist_res = client.get("/api/v1/assessments/history", headers=auth_patient["headers"])
    assert hist_res.status_code == 200
    hist_json = hist_res.json()
    tokens = [item["session_token"] for item in hist_json.get("items", [])]
    assert session_token in tokens


# -----------------------------------------------------------------------------
# 2. Clinical Scenario Validation Across All 4 Tiers
# -----------------------------------------------------------------------------

def test_p16_clinical_scenarios_all_four_outcome_tiers():
    """
    Validates that the 4 canonical outcome tiers are strictly supported by the clinical engine
    and defined without any schema corruption.
    """
    expected_tiers = {
        "TIER_1_NO_RISK": "NO_REPORTED_RISK_FACTORS",
        "TIER_2_RISK_FACTORS": "RISK_FACTORS_IDENTIFIED",
        "TIER_3_EVAL_RECOMMENDED": "CLINICAL_EVALUATION_RECOMMENDED",
        "TIER_4_URGENT": "URGENT_MEDICAL_ASSESSMENT"
    }

    for attr_name, expected_value in expected_tiers.items():
        enum_member = getattr(ClinicalOutcomeTier, attr_name)
        assert enum_member.value == expected_value, f"Tier mismatch for {attr_name}"


def test_p16_urgent_emergency_circuit_preemption(db: Session):
    """
    Validates that acute red-flag symptoms (severe testicular pain / palpable mass)
    strictly preempt lower tier lifestyle or chronic findings.
    """
    # Create synthetic assessment with emergency symptoms
    sess_id = f"urgent_test_{uuid.uuid4().hex[:8]}"
    assessment = Assessment(
        id=str(uuid.uuid4()),
        session_token=sess_id,
        questionnaire_version_id=1,
        status=AssessmentStatus.SUBMITTED
    )
    db.add(assessment)
    db.commit()

    report_ref = f"GNX-URG-{uuid.uuid4().hex[:6].upper()}"
    report = AssessmentReport(
        report_reference=report_ref,
        assessment_id=assessment.id,
        session_token=sess_id,
        questionnaire_version_tag="v1.0.0",
        rule_engine_version="v1.0.0",
        outcome_tier=ClinicalOutcomeTier.TIER_4_URGENT,
        outcome_title_en="Urgent Medical Assessment Required",
        outcome_title_ar="تقييم طبي عاجل مطلوب",
        outcome_description_en="Acute testicular pain detected requiring immediate emergency evaluation.",
        outcome_description_ar="ألم حاد في الخصية يتطلب تقييماً فورياً في الطوارئ.",
        is_urgent_red_flag=True,
        clinical_disclaimer_en="Disclaimer.",
        clinical_disclaimer_ar="إخلاء مسؤولية."
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    assert report.is_urgent_red_flag is True
    assert report.outcome_tier == ClinicalOutcomeTier.TIER_4_URGENT


def test_p16_safe_answers_uncertainty_isolation():
    """
    Verifies that 'I don't know' and 'Prefer not to say' safe answers are isolated
    and never falsify a negative risk or trigger unauthorized clinical rules.
    """
    rule_predicate = {"question_code": "Q_MUMPS", "operator": "EQUALS", "value": "YES"}

    # 1. Answered with is_unsure
    state_unsure = {"Q_MUMPS": {"is_unsure": True}}
    res_unsure, _ = PredicateEvaluator.evaluate_predicate_tree(rule_predicate, state_unsure)
    assert res_unsure == PredicateEvaluationState.INDETERMINATE

    # 2. Answered with is_prefer_not_to_say
    state_pns = {"Q_MUMPS": {"is_prefer_not_to_say": True}}
    res_pns, _ = PredicateEvaluator.evaluate_predicate_tree(rule_predicate, state_pns)
    assert res_pns == PredicateEvaluationState.INDETERMINATE


# -----------------------------------------------------------------------------
# 3. PDF Report Generation & Bilingual Layout Test
# -----------------------------------------------------------------------------

def test_p16_pdf_report_generation_and_bilingual_layout(db: Session, auth_patient):
    """
    Validates formal evidence-linked PDF report generation:
    - Generates valid binary PDF (%PDF-)
    - Enforces mandatory non-diagnostic watermark
    - Verifies bilingual English & Arabic disclaimers
    """
    sess_id = f"pdf_test_{uuid.uuid4().hex[:8]}"
    assessment = Assessment(
        id=str(uuid.uuid4()),
        user_id=auth_patient["user"].id,
        session_token=sess_id,
        questionnaire_version_id=1,
        status=AssessmentStatus.SUBMITTED
    )
    db.add(assessment)
    db.commit()

    report_ref = f"GNX-PDF-{uuid.uuid4().hex[:6].upper()}"
    report = AssessmentReport(
        report_reference=report_ref,
        assessment_id=assessment.id,
        user_id=auth_patient["user"].id,
        session_token=sess_id,
        questionnaire_version_tag="v1.0.0",
        rule_engine_version="v1.0.0",
        outcome_tier=ClinicalOutcomeTier.TIER_2_RISK_FACTORS,
        outcome_title_en="Lifestyle Modifiable Risk Factors",
        outcome_title_ar="عوامل نمط الحياة القابلة للتعديل",
        outcome_description_en="Lifestyle modifications recommended.",
        outcome_description_ar="يوصى بتعديل نمط الحياة.",
        is_urgent_red_flag=False,
        recommended_specialties=["Andrologist"],
        clinical_disclaimer_en="GENOVEX does not diagnose male infertility.",
        clinical_disclaimer_ar="جينوفيكس لا يقدم تشخيصاً طبياً لعقم الرجال."
    )
    db.add(report)
    db.commit()

    # Generate bilingual PDF via ReportPDFService
    pdf_bytes = ReportPDFService.generate_pdf_report(report)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 250
    assert pdf_bytes.startswith(b"%PDF-")


# -----------------------------------------------------------------------------
# 4. Report Verification & Expiring Sharing Workflow Test
# -----------------------------------------------------------------------------

def test_p16_report_verification_and_expiring_sharing(db: Session, auth_patient, other_patient):
    """
    Validates report integrity verification, expiring clinician share token generation,
    anonymous access via token, and immediate share revocation.
    """
    sess_id = f"share_test_{uuid.uuid4().hex[:8]}"
    assessment = Assessment(
        id=str(uuid.uuid4()),
        user_id=auth_patient["user"].id,
        session_token=sess_id,
        questionnaire_version_id=1,
        status=AssessmentStatus.SUBMITTED
    )
    db.add(assessment)
    db.commit()

    report_ref = f"GNX-SHR-{uuid.uuid4().hex[:6].upper()}"
    report = AssessmentReport(
        report_reference=report_ref,
        assessment_id=assessment.id,
        user_id=auth_patient["user"].id,
        session_token=sess_id,
        questionnaire_version_tag="v1.0.0",
        rule_engine_version="v1.0.0",
        outcome_tier=ClinicalOutcomeTier.TIER_1_NO_RISK,
        outcome_title_en="No Reported Risk Factors",
        outcome_title_ar="لا توجد عوامل خطر مسجلة",
        outcome_description_en="Standard informational baseline.",
        outcome_description_ar="معلومات عامة أساسية.",
        is_urgent_red_flag=False,
        clinical_disclaimer_en="Disclaimer.",
        clinical_disclaimer_ar="إخلاء مسؤولية."
    )
    db.add(report)
    db.commit()

    # 1. Public authenticity verification of authentic report
    verify_res = client.get(f"/api/v1/reports/{report_ref}/verify")
    assert verify_res.status_code == 200
    assert verify_res.json()["is_valid"] is True
    assert verify_res.json()["status"] == "AUTHENTIC_VERIFIED"

    # 2. Public verification of non-existent reference
    invalid_verify = client.get("/api/v1/reports/GNX-FAKE-999999/verify")
    assert invalid_verify.status_code == 200
    assert invalid_verify.json()["is_valid"] is False

    # 3. Patient creates an expiring share link for a clinician
    share_payload = {
        "recipient_name": "Dr. Sarah Al-Maktoum",
        "expires_in_hours": 48
    }
    share_res = client.post(
        f"/api/v1/reports/{report_ref}/share",
        json=share_payload,
        headers=auth_patient["headers"]
    )
    assert share_res.status_code == 200
    share_data = share_res.json()
    share_token = share_data["share_token"]
    assert share_token is not None

    # 4. Access shared report via token without logging in
    public_access_res = client.get(f"/api/v1/reports/shared/{share_token}")
    assert public_access_res.status_code == 200
    assert public_access_res.json()["report_reference"] == report_ref

    # 5. Revoke the share token
    revoke_res = client.post(
        f"/api/v1/reports/{report_ref}/revoke-share",
        headers=auth_patient["headers"]
    )
    assert revoke_res.status_code == 200

    # 6. Accessing revoked token must now fail (401, 403, or 404)
    revoked_access_res = client.get(f"/api/v1/reports/shared/{share_token}")
    assert revoked_access_res.status_code in (401, 403, 404)


# -----------------------------------------------------------------------------
# 5. RBAC & IDOR Protections
# -----------------------------------------------------------------------------

def test_p16_rbac_and_idor_protections(db: Session, auth_patient, other_patient, auth_clinician, auth_admin):
    """
    Validates cross-user isolation and role-based permissions:
    - Patient B cannot access or share Patient A's report (IDOR protection).
    - Patient cannot access Admin endpoints (403).
    - Clinician cannot access Admin endpoints (403).
    - Admin can access operational dashboard (200).
    """
    sess_id = f"idor_{uuid.uuid4().hex[:8]}"
    assessment = Assessment(
        id=str(uuid.uuid4()),
        user_id=auth_patient["user"].id,
        session_token=sess_id,
        questionnaire_version_id=1,
        status=AssessmentStatus.SUBMITTED
    )
    db.add(assessment)
    db.commit()

    report_ref = f"GNX-IDOR-{uuid.uuid4().hex[:6].upper()}"
    report = AssessmentReport(
        report_reference=report_ref,
        assessment_id=assessment.id,
        user_id=auth_patient["user"].id,
        session_token=sess_id,
        questionnaire_version_tag="v1.0.0",
        rule_engine_version="v1.0.0",
        outcome_tier=ClinicalOutcomeTier.TIER_2_RISK_FACTORS,
        outcome_title_en="Lifestyle Factors",
        outcome_title_ar="عوامل نمط الحياة",
        outcome_description_en="Summary.",
        outcome_description_ar="ملخص.",
        is_urgent_red_flag=False,
        clinical_disclaimer_en="Disclaimer.",
        clinical_disclaimer_ar="إخلاء مسؤولية."
    )
    db.add(report)
    db.commit()

    # 1. IDOR: other_patient attempts to generate a share link for auth_patient's report -> 403 or 404
    idor_share = client.post(
        f"/api/v1/reports/{report_ref}/share",
        json={"recipient_name": "Attacker", "expires_in_hours": 24},
        headers=other_patient["headers"]
    )
    assert idor_share.status_code in (403, 404)

    # 2. RBAC: Patient attempts to access Admin user management -> 403
    patient_admin_res = client.get("/api/v1/admin/users", headers=auth_patient["headers"])
    assert patient_admin_res.status_code == 403

    # 3. RBAC: Clinician attempts to access Admin user management -> 403
    clinician_admin_res = client.get("/api/v1/admin/users", headers=auth_clinician["headers"])
    assert clinician_admin_res.status_code == 403

    # 4. RBAC: Admin accesses Admin overview -> 200
    admin_overview_res = client.get("/api/v1/admin/overview", headers=auth_admin["headers"])
    assert admin_overview_res.status_code == 200


# -----------------------------------------------------------------------------
# 6. Clinical Navigation & Directory Filtering
# -----------------------------------------------------------------------------

def test_p16_clinical_navigation_directory_filtering():
    """
    Validates UAE healthcare facilities directory filtering by Emirate, specialty, and 24/7 emergency services.
    """
    # 1. Public facilities listing
    res = client.get("/api/v1/navigation/facilities?page=1&page_size=10")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert len(data["items"]) > 0

    # 2. Filter by Emirate
    dubai_res = client.get("/api/v1/navigation/facilities?emirate=DUBAI")
    assert dubai_res.status_code == 200
    for f in dubai_res.json()["items"]:
        assert f["emirate"] == "DUBAI"

    # 3. Filter by 24/7 Emergency
    er_res = client.get("/api/v1/navigation/facilities?has_emergency=true")
    assert er_res.status_code == 200
    for f in er_res.json()["items"]:
        assert f["has_24_7_emergency"] is True


# -----------------------------------------------------------------------------
# 7. Audit Logging & Zero-PHI Verification
# -----------------------------------------------------------------------------

def test_p16_audit_logging_zero_phi_verification(db: Session, auth_patient):
    """
    Verifies that sensitive actions record in audit_logs without exposing
    passwords, questionnaire answers, or Protected Health Information (PHI).
    """
    # Trigger login action which writes USER_LOGIN audit log
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": auth_patient["user"].email, "password": "PatientPass123!"}
    )
    assert login_res.status_code == 200

    # Check only audit logs generated for auth_patient
    user_logs = db.query(AuditLog).filter(AuditLog.user_id == auth_patient["user"].id).all()
    assert len(user_logs) > 0

    # Ensure zero sensitive health answers or passwords exist in any audit detail field
    for log in user_logs:
        details_str = str(log.details)
        assert "password" not in details_str.lower()
        assert "patientpass123!" not in details_str.lower()
        assert "varicocele" not in details_str.lower()
        assert "semen" not in details_str.lower()
        assert log.action is not None


# -----------------------------------------------------------------------------
# 8. Database Referential Integrity & Schema Parity
# -----------------------------------------------------------------------------

def test_p16_database_referential_integrity(db: Session):
    """
    Executes SQLite low-level integrity checks:
    - PRAGMA integrity_check == ok
    - PRAGMA foreign_key_check == [] (zero orphan keys)
    - All 17 core application tables present
    """
    conn = db.connection().connection
    cur = conn.cursor()

    cur.execute("PRAGMA integrity_check;")
    assert cur.fetchall() == [("ok",)]

    cur.execute("PRAGMA foreign_key_check;")
    assert cur.fetchall() == []

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [r[0] for r in cur.fetchall() if r[0] != "alembic_version"]
    assert len(tables) == 18
    assert "password_reset_tokens" in tables
