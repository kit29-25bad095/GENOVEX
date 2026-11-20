import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.security import User, RoleEnum, get_password_hash, create_access_token
from app.models.questionnaire import Assessment, AssessmentStatus
from app.models.assessment_report import AssessmentReport, ClinicalOutcomeTier
from app.models.clinical_rules import ClinicalRule, ClinicalRuleStatus
from app.services.report_pdf_service import ReportPDFService
from main import app

client = TestClient(app)

@pytest.fixture
def test_users(db: Session):
    u1 = db.query(User).filter(User.email == "patient_p13_a@genovex.ae").first()
    if not u1:
        u1 = User(
            email="patient_p13_a@genovex.ae",
            hashed_password=get_password_hash("Pass123!"),
            full_name="Patient P13 A",
            role=RoleEnum.PATIENT,
            is_active=True
        )
        db.add(u1)
        db.commit()
        db.refresh(u1)

    u2 = db.query(User).filter(User.email == "patient_p13_b@genovex.ae").first()
    if not u2:
        u2 = User(
            email="patient_p13_b@genovex.ae",
            hashed_password=get_password_hash("Pass123!"),
            full_name="Patient P13 B",
            role=RoleEnum.PATIENT,
            is_active=True
        )
        db.add(u2)
        db.commit()
        db.refresh(u2)

    clinician = db.query(User).filter(User.email == "clinician_p13@genovex.ae").first()
    if not clinician:
        clinician = User(
            email="clinician_p13@genovex.ae",
            hashed_password=get_password_hash("ClinPass123!"),
            full_name="Dr. P13 Clinician",
            role=RoleEnum.CLINICIAN,
            is_active=True
        )
        db.add(clinician)
        db.commit()
        db.refresh(clinician)

    t1 = create_access_token(data={"sub": u1.email, "role": u1.role.value, "uid": u1.id})
    t2 = create_access_token(data={"sub": u2.email, "role": u2.role.value, "uid": u2.id})
    tc = create_access_token(data={"sub": clinician.email, "role": clinician.role.value, "uid": clinician.id})

    return {
        "user_a": u1,
        "user_b": u2,
        "clinician": clinician,
        "headers_a": {"Authorization": f"Bearer {t1}"},
        "headers_b": {"Authorization": f"Bearer {t2}"},
        "headers_clinician": {"Authorization": f"Bearer {tc}"}
    }

def test_assessment_history_requires_authentication():
    """AC01: Verifies that assessment history endpoint is protected by authentication."""
    response = client.get("/api/v1/assessment/history")
    assert response.status_code == 401

def test_assessment_history_user_isolation(test_users, db: Session):
    """
    AC02: Verifies strict user isolation (IDOR protection) on assessment history.
    User A sees only User A's assessments; User B cannot see User A's history.
    """
    u_a = test_users["user_a"]
    u_b = test_users["user_b"]

    # Create assessment for User A
    a_a = Assessment(
        id="p13-assess-a-uuid",
        user_id=u_a.id,
        session_token="p13_token_user_a",
        questionnaire_version_id=1,
        status=AssessmentStatus.SUBMITTED,
        started_at=datetime.now(timezone.utc)
    )
    db.add(a_a)

    # Create assessment for User B
    a_b = Assessment(
        id="p13-assess-b-uuid",
        user_id=u_b.id,
        session_token="p13_token_user_b",
        questionnaire_version_id=1,
        status=AssessmentStatus.IN_PROGRESS,
        started_at=datetime.now(timezone.utc)
    )
    db.add(a_b)
    db.commit()

    # User A query
    res_a = client.get("/api/v1/assessment/history", headers=test_users["headers_a"])
    assert res_a.status_code == 200
    data_a = res_a.json()
    assert any(item["session_token"] == "p13_token_user_a" for item in data_a["items"])
    assert not any(item["session_token"] == "p13_token_user_b" for item in data_a["items"])

    # User B query
    res_b = client.get("/api/v1/assessment/history", headers=test_users["headers_b"])
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert any(item["session_token"] == "p13_token_user_b" for item in data_b["items"])
    assert not any(item["session_token"] == "p13_token_user_a" for item in data_b["items"])

def test_claim_guest_assessment_success(test_users, db: Session):
    """AC03: Verifies claiming an unassociated guest assessment session."""
    u_a = test_users["user_a"]
    guest_token = "p13_guest_unclaimed_token_1"

    # Create anonymous guest assessment
    guest_assessment = Assessment(
        id="p13-guest-assess-uuid",
        user_id=None,
        session_token=guest_token,
        questionnaire_version_id=1,
        status=AssessmentStatus.SUBMITTED
    )
    db.add(guest_assessment)
    db.commit()

    # Claim by User A
    res = client.post(f"/api/v1/assessment/{guest_token}/claim", headers=test_users["headers_a"])
    assert res.status_code == 200
    assert res.json()["status"] == "success"

    # Verify DB ownership updated
    db.refresh(guest_assessment)
    assert guest_assessment.user_id == u_a.id

def test_claim_assessment_already_owned_rejected(test_users, db: Session):
    """AC04: Verifies that claiming an assessment already owned by another user is rejected with 403."""
    u_a = test_users["user_a"]
    token = "p13_owned_by_a_token"

    owned_assessment = Assessment(
        id="p13-owned-by-a-uuid",
        user_id=u_a.id,
        session_token=token,
        questionnaire_version_id=1,
        status=AssessmentStatus.SUBMITTED
    )
    db.add(owned_assessment)
    db.commit()

    # User B attempts to claim User A's assessment
    res = client.post(f"/api/v1/assessment/{token}/claim", headers=test_users["headers_b"])
    assert res.status_code == 403
    assert "already linked" in res.json()["detail"].lower()

def test_pdf_report_service_generation(db: Session):
    """
    AC05: Verifies that ReportPDFService compiles valid non-empty PDF bytes
    containing standard PDF magic bytes (%PDF-).
    """
    report = AssessmentReport(
        report_reference="GNX-RPT-PDF-TEST-01",
        assessment_id="test-p13-pdf-assessment",
        session_token="p13_pdf_token_01",
        questionnaire_version_tag="v1.0.0",
        rule_engine_version="v1.0.0",
        outcome_tier=ClinicalOutcomeTier.TIER_2_RISK_FACTORS,
        outcome_title_en="Lifestyle Modifiable Risk Factors",
        outcome_title_ar="عوامل نمط الحياة القابلة للتعديل",
        outcome_description_en="Multiple lifestyle factors identified that impact sperm parameters.",
        outcome_description_ar="تم تحديد عوامل في نمط الحياة قد تؤثر على جودة السائل المنوي.",
        is_urgent_red_flag=False,
        recommended_specialties=["Male Reproductive Urologist / Andrologist"],
        recommended_next_steps_en=["Consider lifestyle modifications", "Repeat semen analysis in 3 months"],
        recommended_next_steps_ar=["مراجعة نمط الحياة", "إعادة فحص السائل المنوي بعد 3 أشهر"],
        identified_risk_factors_json=[
            {"factor_code": "SMOKING", "domain": "lifestyle", "title_en": "Tobacco Use", "severity": "MODERATE"}
        ],
        evidence_citations_json=[
            {"title": "EAU Guidelines on Male Sexual and Reproductive Health (2024)"}
        ],
        clinical_disclaimer_en="Non-diagnostic advisory report.",
        clinical_disclaimer_ar="تقرير استرشادي غير تشخيصي."
    )

    pdf_bytes = ReportPDFService.generate_pdf_report(report)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF-")

def test_pdf_download_governance_withholding_persists(test_users, db: Session):
    """
    AC06: Verifies that patient-facing PDF download route enforces centralized
    clinical governance withholding (HTTP 422) when rules are unapproved.
    """
    token = "p13_pdf_withheld_token"
    u_a = test_users["user_a"]

    assessment = Assessment(
        id="p13-pdf-withheld-assess",
        user_id=u_a.id,
        session_token=token,
        questionnaire_version_id=1,
        status=AssessmentStatus.SUBMITTED
    )
    db.add(assessment)

    report = AssessmentReport(
        report_reference="GNX-RPT-PDF-WITHHELD",
        assessment_id=assessment.id,
        user_id=u_a.id,
        session_token=token,
        questionnaire_version_tag="v1.0.0",
        rule_engine_version="v1.0.0",
        outcome_tier=ClinicalOutcomeTier.TIER_2_RISK_FACTORS,
        outcome_title_en="Lifestyle Risk Factors",
        outcome_title_ar="عوامل الخطر",
        outcome_description_en="Summary.",
        outcome_description_ar="ملخص.",
        is_urgent_red_flag=False,
        clinical_disclaimer_en="Disclaimer.",
        clinical_disclaimer_ar="إخلاء مسؤولية."
    )
    db.add(report)
    db.commit()

    # Patient user requests PDF download -> Withheld under HTTP 422
    res = client.get(f"/api/v1/assessment/{token}/report/pdf", headers=test_users["headers_a"])
    assert res.status_code == 422
    assert "CLINICAL_RELEASE_WITHHELD" in str(res.json())

def test_pdf_download_authorized_clinician_access(test_users, db: Session):
    """
    AC07: Verifies that authorized clinician / audit users CAN download PDF report
    with valid application/pdf binary content header.
    """
    token = "p13_pdf_clinician_token"

    assessment = Assessment(
        id="p13-pdf-clinician-assess",
        user_id=None,
        session_token=token,
        questionnaire_version_id=1,
        status=AssessmentStatus.SUBMITTED
    )
    db.add(assessment)

    report = AssessmentReport(
        report_reference="GNX-RPT-PDF-CLINICIAN",
        assessment_id=assessment.id,
        session_token=token,
        questionnaire_version_tag="v1.0.0",
        rule_engine_version="v1.0.0",
        outcome_tier=ClinicalOutcomeTier.TIER_3_EVAL_RECOMMENDED,
        outcome_title_en="Clinical Evaluation Recommended",
        outcome_title_ar="يوصى بالتقييم الإكلينيكي",
        outcome_description_en="Specialist evaluation recommended.",
        outcome_description_ar="يوصى بمراجعة استشاري.",
        is_urgent_red_flag=False,
        clinical_disclaimer_en="Disclaimer.",
        clinical_disclaimer_ar="إخلاء مسؤولية."
    )
    db.add(report)
    db.commit()

    res = client.get(f"/api/v1/assessment/{token}/report/pdf", headers=test_users["headers_clinician"])
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert "attachment; filename=\"GENOVEX-Report-GNX-RPT-PDF-CLINICIAN.pdf\"" in res.headers["content-disposition"]
    assert res.content.startswith(b"%PDF-")
