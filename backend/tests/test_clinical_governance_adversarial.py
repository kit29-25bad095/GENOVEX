"""
GENOVEX: Adversarial Clinical Governance Test Suite
Verifies centralized fail-closed clinical governance withholding across all edge cases,
caller roles, all 4 outcome tiers, and patient-facing report & AI routes.
"""

import uuid
import pytest
from datetime import datetime, timezone
from fastapi import status, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.questionnaire import (
    Assessment, AssessmentResponse, Question, QuestionnaireVersion,
    AssessmentStatus, QuestionnaireStatus
)
from app.models.clinical_rules import (
    ClinicalRule, ClinicalOutcomeTier, ClinicalRuleStatus
)
from app.models.assessment_report import AssessmentReport
from app.core.security import User, RoleEnum, create_access_token, AuditLog
from app.services.assessment_processing_service import ClinicalGovernanceGate, AssessmentProcessingService
from app.services.clinical_rule_engine import ClinicalRuleEngineService
from main import app as fastapi_app


@pytest.fixture
def test_client():
    return TestClient(fastapi_app)


@pytest.fixture
def setup_gov_db(db: Session):
    """Sets up an assessment and sample rules in disposable sandbox."""
    q_version = db.query(QuestionnaireVersion).first()
    token = f"gov_adv_{uuid.uuid4().hex}"
    assessment = Assessment(
        session_token=token,
        questionnaire_version_id=q_version.id,
        status=AssessmentStatus.LOCKED
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return db, assessment, token


def _create_test_report(db: Session, assessment_id: str, session_token: str, tier: ClinicalOutcomeTier) -> AssessmentReport:
    """Helper to create a valid AssessmentReport adhering to all NOT NULL database constraints."""
    report = AssessmentReport(
        assessment_id=assessment_id,
        report_reference=f"GNX-ADV-{uuid.uuid4().hex[:6].upper()}",
        session_token=session_token,
        outcome_tier=tier,
        outcome_title_en="Test Outcome",
        outcome_title_ar="النتيجة",
        outcome_description_en="Description",
        outcome_description_ar="الوصف",
        questionnaire_version_tag="v1.0",
        rule_engine_version="1.0.0",
        identified_risk_factors_json=[],
        triggered_rules_snapshot_json=[],
        responses_summary_json=[],
        evidence_citations_json=[],
        clinical_disclaimer_en="GENOVEX provides risk identification only.",
        clinical_disclaimer_ar="يقدم جينوفيكس تحديد المخاطر والتوجيه السريري فقط.",
        is_locked=True,
        generated_at=datetime.now(timezone.utc)
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


# ---------------------------------------------------------------------------
# Test 1: Null Reviewer ID Fails Closed
# ---------------------------------------------------------------------------
def test_gov_01_null_reviewer_id_fails_closed(setup_gov_db):
    db, assessment, token = setup_gov_db
    rule = db.query(ClinicalRule).first()
    rule.clinical_reviewer_id = None
    rule.approved_at = datetime.now(timezone.utc)
    db.commit()

    assert ClinicalGovernanceGate.is_rule_verifiably_approved(db, rule) is False


# ---------------------------------------------------------------------------
# Test 2: Synthetic Reviewer ID (e.g. User 16) Fails Closed
# ---------------------------------------------------------------------------
def test_gov_02_synthetic_reviewer_id_fails_closed(setup_gov_db):
    db, assessment, token = setup_gov_db
    # Create synthetic audit clinician
    synth_user = User(
        email="audit_clinician_synth@example.com",
        full_name="Dr. Audit Synthetic",
        role=RoleEnum.CLINICIAN,
        hashed_password="hash",
        is_active=True
    )
    db.add(synth_user)
    db.commit()

    rule = db.query(ClinicalRule).first()
    rule.clinical_reviewer_id = synth_user.id
    rule.approved_at = datetime.now(timezone.utc)
    db.commit()

    assert ClinicalGovernanceGate.is_rule_verifiably_approved(db, rule) is False


# ---------------------------------------------------------------------------
# Test 3: Non-null Reviewer without Approval Audit Evidence Fails Closed
# ---------------------------------------------------------------------------
def test_gov_03_reviewer_without_audit_evidence_fails_closed(setup_gov_db):
    db, assessment, token = setup_gov_db
    # Legitimate looking name, but no approval audit log entry exists
    clin_user = User(
        email="dr.mohammed.alblooshi@genovex.ae",
        full_name="Dr. Mohammed Al Blooshi",
        role=RoleEnum.CLINICIAN,
        hashed_password="hash",
        is_active=True
    )
    db.add(clin_user)
    db.commit()

    rule = db.query(ClinicalRule).first()
    rule.clinical_reviewer_id = clin_user.id
    rule.approved_at = datetime.now(timezone.utc)
    db.commit()

    # Without formal audit sign-off in audit_logs, fails closed
    assert ClinicalGovernanceGate.is_rule_verifiably_approved(db, rule) is False


# ---------------------------------------------------------------------------
# Test 4: Approval Timestamp Without Verified Provenance Fails Closed
# ---------------------------------------------------------------------------
def test_gov_04_timestamp_without_provenance_fails_closed(setup_gov_db):
    db, assessment, token = setup_gov_db
    rule = db.query(ClinicalRule).first()
    rule.approved_at = datetime.now(timezone.utc)
    rule.clinical_reviewer_id = None
    db.commit()

    assert ClinicalGovernanceGate.is_rule_verifiably_approved(db, rule) is False


# ---------------------------------------------------------------------------
# Test 5: Published Status Without Clinician Approval Fails Closed
# ---------------------------------------------------------------------------
def test_gov_05_published_status_without_approval_fails_closed(setup_gov_db):
    db, assessment, token = setup_gov_db
    rule = db.query(ClinicalRule).first()
    rule.status = ClinicalRuleStatus.PUBLISHED
    rule.clinical_reviewer_id = None
    db.commit()

    assert ClinicalGovernanceGate.is_rule_verifiably_approved(db, rule) is False


# ---------------------------------------------------------------------------
# Test 6: Missing Reviewer Record in Users Table Fails Closed
# ---------------------------------------------------------------------------
def test_gov_06_missing_reviewer_user_record_fails_closed(setup_gov_db):
    db, assessment, token = setup_gov_db
    rule = db.query(ClinicalRule).first()
    # Set non-existent reviewer on model without committing orphan FK to DB
    rule.clinical_reviewer_id = 999999  # Non-existent user id
    rule.approved_at = datetime.now(timezone.utc)

    # Must query and fail closed when reviewer is not in users table
    assert ClinicalGovernanceGate.is_rule_verifiably_approved(db, rule) is False
    db.rollback()


# ---------------------------------------------------------------------------
# Test 7: Legitimate Provenance Satisfies Verification in Sandbox
# ---------------------------------------------------------------------------
def test_gov_07_legitimate_approval_provenance_satisfies_verification(setup_gov_db):
    db, assessment, token = setup_gov_db
    legit_clinician = User(
        email="dr.khalid.alzaabi@genovex.ae",
        full_name="Dr. Khalid Al Zaabi",
        role=RoleEnum.CLINICIAN,
        hashed_password="hash",
        is_active=True
    )
    db.add(legit_clinician)
    db.commit()

    rule = db.query(ClinicalRule).first()
    rule.clinical_reviewer_id = legit_clinician.id
    rule.approved_at = datetime.now(timezone.utc)

    # Add verified clinical approval audit record
    audit_signoff = AuditLog(
        user_id=legit_clinician.id,
        user_email=legit_clinician.email,
        user_role="CLINICIAN",
        action="CLINICAL_RULE_APPROVE",
        resource_type="ClinicalRule",
        resource_id=rule.rule_code,
        details={"approved_rule_code": rule.rule_code, "signoff": "Verified UAE MOHAP Consultant"},
        timestamp=datetime.now(timezone.utc)
    )
    db.add(audit_signoff)
    db.commit()

    assert ClinicalGovernanceGate.is_rule_verifiably_approved(db, rule) is True


# ---------------------------------------------------------------------------
# Test 8-11: All 4 Outcome Tiers Withheld When Rules Are Unapproved
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("tier_to_test", [
    ClinicalOutcomeTier.TIER_1_NO_RISK,
    ClinicalOutcomeTier.TIER_2_RISK_FACTORS,
    ClinicalOutcomeTier.TIER_3_EVAL_RECOMMENDED,
    ClinicalOutcomeTier.TIER_4_URGENT
])
def test_gov_all_four_tiers_withheld_when_unapproved(setup_gov_db, test_client, tier_to_test):
    db, assessment, token = setup_gov_db
    report = _create_test_report(db, assessment.id, token, tier_to_test)

    # Anonymous / Patient caller must receive HTTP 422 CLINICAL_RELEASE_WITHHELD
    resp = test_client.get(f"/api/v1/assessment/{token}/report")
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert resp.json()["detail"]["code"] == "CLINICAL_RELEASE_WITHHELD"


# ---------------------------------------------------------------------------
# Test 12: Every Patient-Facing Route Enforces Governance
# ---------------------------------------------------------------------------
def test_gov_all_patient_facing_routes_enforce_governance(setup_gov_db, test_client):
    db, assessment, token = setup_gov_db
    report = _create_test_report(db, assessment.id, token, ClinicalOutcomeTier.TIER_2_RISK_FACTORS)

    # 1. Primary report route
    r1 = test_client.get(f"/api/v1/assessment/{token}/report")
    assert r1.status_code == 422
    assert r1.json()["detail"]["code"] == "CLINICAL_RELEASE_WITHHELD"

    # 2. Sanitized ID report route
    r2 = test_client.get(
        f"/api/v1/questionnaire/assessments/{assessment.id}/report",
        headers={"X-Session-Token": token}
    )
    assert r2.status_code == 422
    assert r2.json()["detail"]["code"] == "CLINICAL_RELEASE_WITHHELD"

    # 3. AI Result explanation route
    r3 = test_client.post(
        "/api/v1/ai/explain-result",
        json={"report_reference": report.report_reference, "session_token": token, "language": "en"}
    )
    assert r3.status_code == 422
    assert r3.json()["detail"]["code"] == "CLINICAL_RELEASE_WITHHELD"

    # 4. AI Preparation questions route
    r4 = test_client.post(
        "/api/v1/ai/preparation-questions",
        json={"report_reference": report.report_reference, "session_token": token, "language": "en"}
    )
    assert r4.status_code == 422
    assert r4.json()["detail"]["code"] == "CLINICAL_RELEASE_WITHHELD"


# ---------------------------------------------------------------------------
# Test 13: Caller-Controlled Bypass Attempts Are Completely Ineffective
# ---------------------------------------------------------------------------
def test_gov_caller_bypass_attempts_are_ignored(setup_gov_db, test_client):
    db, assessment, token = setup_gov_db
    report = _create_test_report(db, assessment.id, token, ClinicalOutcomeTier.TIER_2_RISK_FACTORS)

    # Attempt 1: Query parameter ?patient_facing=false
    r1 = test_client.get(f"/api/v1/assessment/{token}/report?patient_facing=false")
    assert r1.status_code == 422

    # Attempt 2: Query parameter ?audit_mode=true
    r2 = test_client.get(f"/api/v1/assessment/{token}/report?audit_mode=true")
    assert r2.status_code == 422

    # Attempt 3: Header override X-Role: CLINICIAN without valid JWT
    r3 = test_client.get(
        f"/api/v1/assessment/{token}/report",
        headers={"X-Role": "CLINICIAN", "X-Bypass-Governance": "true"}
    )
    assert r3.status_code == 422


# ---------------------------------------------------------------------------
# Test 14: Clinician Role Can Access in Clinical Audit Mode
# ---------------------------------------------------------------------------
def test_gov_clinician_accesses_in_audit_mode(setup_gov_db, test_client):
    db, assessment, token = setup_gov_db
    report = _create_test_report(db, assessment.id, token, ClinicalOutcomeTier.TIER_3_EVAL_RECOMMENDED)

    # Create authorized clinician user and JWT
    clin_user = User(
        email="dr.review@genovex.ae",
        full_name="Dr. Clinical Auditor",
        role=RoleEnum.CLINICIAN,
        hashed_password="hash",
        is_active=True
    )
    db.add(clin_user)
    db.commit()

    token_jwt = create_access_token({"sub": clin_user.email})

    # Clinician receives HTTP 200 OK
    resp = test_client.get(
        f"/api/v1/assessment/{token}/report",
        headers={"Authorization": f"Bearer {token_jwt}"}
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["report_reference"] == report.report_reference
