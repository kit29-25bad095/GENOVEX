import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone
try:
    import pymupdf
except ImportError:
    try:
        import fitz as pymupdf
    except ImportError:
        pymupdf = None

from app.core.security import User, RoleEnum, get_password_hash, create_access_token, AuditLog
from app.models.questionnaire import Assessment, AssessmentStatus
from app.models.assessment_report import AssessmentReport, ClinicalOutcomeTier
from app.models.clinical_rules import ClinicalRule, ClinicalRuleStatus
from app.services.report_pdf_service import ReportPDFService
from app.services.report_sharing_service import ReportSharingService
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

# -----------------------------------------------------------------------------
# 1. Assessment History & IDOR Tests
# -----------------------------------------------------------------------------
def test_assessment_history_requires_authentication():
    """AC01: Verifies that assessment history endpoint is protected by authentication."""
    response = client.get("/api/v1/assessment/history")
    assert response.status_code == 401

    # Also verify plural route
    response_plural = client.get("/api/v1/assessments/history")
    assert response_plural.status_code == 401

def test_assessment_history_user_isolation(test_users, db: Session):
    """
    AC02: Verifies strict user isolation (IDOR protection) on assessment history.
    User A sees only User A's assessments; User B cannot see User A's history.
    """
    u_a = test_users["user_a"]
    u_b = test_users["user_b"]

    a_a = Assessment(
        id="p13-assess-a-uuid",
        user_id=u_a.id,
        session_token="p13_token_user_a",
        questionnaire_version_id=1,
        status=AssessmentStatus.SUBMITTED,
        started_at=datetime.now(timezone.utc)
    )
    db.add(a_a)

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

    # User A query (both singular and plural)
    res_a = client.get("/api/v1/assessment/history", headers=test_users["headers_a"])
    assert res_a.status_code == 200
    data_a = res_a.json()
    assert any(item["session_token"] == "p13_token_user_a" for item in data_a["items"])
    assert not any(item["session_token"] == "p13_token_user_b" for item in data_a["items"])

    res_a_plural = client.get("/api/v1/assessments/history", headers=test_users["headers_a"])
    assert res_a_plural.status_code == 200
    assert any(item["session_token"] == "p13_token_user_a" for item in res_a_plural.json()["items"])

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

    guest_assessment = Assessment(
        id="p13-guest-assess-uuid",
        user_id=None,
        session_token=guest_token,
        questionnaire_version_id=1,
        status=AssessmentStatus.SUBMITTED
    )
    db.add(guest_assessment)
    db.commit()

    res = client.post(f"/api/v1/assessment/{guest_token}/claim", headers=test_users["headers_a"])
    assert res.status_code == 200
    assert res.json()["status"] == "success"

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

    res = client.post(f"/api/v1/assessment/{token}/claim", headers=test_users["headers_b"])
    assert res.status_code == 403
    assert "already linked" in res.json()["detail"].lower()

# -----------------------------------------------------------------------------
# 2. PDF Report Generation, Watermark & 5-Point Disclaimer Tests
# -----------------------------------------------------------------------------
def test_pdf_report_service_generation(db: Session):
    """
    AC05: Verifies that ReportPDFService compiles valid non-empty PDF bytes
    containing standard PDF magic bytes (%PDF-), watermark, and mandatory disclaimers.
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
        responses_summary_json=[
            {"question_key": "smoking_status", "prompt_en": "Do you smoke?", "answer_display_en": "Yes", "is_unsure": False, "is_prefer_not_to_say": False}
        ],
        evidence_citations_json=[
            {"title": "EAU Guidelines on Male Sexual and Reproductive Health (2024)"}
        ],
        clinical_disclaimer_en="Non-diagnostic advisory report.",
        clinical_disclaimer_ar="تقرير استرشادي غير تشخيصي."
    )

    pdf_bytes = ReportPDFService.generate_pdf_report(report)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 250
    assert pdf_bytes.startswith(b"%PDF-")

    # If PyMuPDF is available, verify page text content
    if pymupdf is not None:
        doc = pymupdf.open("pdf", pdf_bytes)
        assert len(doc) == 2  # Exactly 2 pages

        # Verify Watermark present on both pages
        p1_text = doc[0].get_text().replace('\xa0', ' ').replace('\xad', '-')
        p2_text = doc[1].get_text().replace('\xa0', ' ').replace('\xad', '-')
        assert "GENOVEX INFORMATIONAL HEALTH REPORT" in p1_text
        assert "NOT A DIAGNOSTIC OPINION" in p1_text
        assert "GENOVEX INFORMATIONAL HEALTH REPORT" in p2_text

        # Verify 5 mandatory disclaimer points in Page 2
        assert "GENOVEX does not diagnose infertility." in p2_text
        assert "GENOVEX does not measure sperm count" in p2_text
        assert "low-risk questionnaire outcome does not establish normal fertility" in p2_text
        assert "not a replacement for professional medical evaluation" in p2_text
        assert "Clinical decisions must be made by qualified healthcare professionals" in p2_text

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

# -----------------------------------------------------------------------------
# 3. Report Integrity & Public Verification Tests
# -----------------------------------------------------------------------------
def test_report_verification_authentic(test_users, db: Session):
    """
    AC08: Verifies public report verification endpoint.
    Returns authentic status, cryptographic hash, and minimal non-sensitive data.
    ZERO PHI LEAKAGE: Never returns user names or answers.
    """
    u_a = test_users["user_a"]
    ref = "GNX-RPT-VERIFY-01"

    assessment = Assessment(
        id="p13-verify-assess-uuid",
        user_id=u_a.id,
        session_token="p13_verify_token",
        questionnaire_version_id=1,
        status=AssessmentStatus.SUBMITTED
    )
    db.add(assessment)

    report = AssessmentReport(
        report_reference=ref,
        assessment_id=assessment.id,
        user_id=u_a.id,
        session_token=assessment.session_token,
        questionnaire_version_tag="v1.0.0",
        rule_engine_version="v1.0.0",
        outcome_tier=ClinicalOutcomeTier.TIER_2_RISK_FACTORS,
        outcome_title_en="Lifestyle Modifiable Factors",
        outcome_title_ar="عوامل نمط الحياة",
        outcome_description_en="Summary.",
        outcome_description_ar="ملخص.",
        is_urgent_red_flag=False,
        clinical_disclaimer_en="Disclaimer.",
        clinical_disclaimer_ar="إخلاء مسؤولية."
    )
    db.add(report)
    db.commit()

    res = client.get(f"/api/v1/reports/{ref}/verify")
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is True
    assert data["status"] == "AUTHENTIC_VERIFIED"
    assert data["report_reference"] == ref
    assert data["questionnaire_version_tag"] == "v1.0.0"
    assert data["rule_engine_version"] == "v1.0.0"
    assert data["integrity_hash"] is not None
    assert len(data["integrity_hash"]) == 64  # Valid SHA-256

    # Verify zero PHI in response
    assert "user_id" not in data
    assert "patient_name" not in data
    assert "email" not in data
    assert "responses" not in data

def test_report_verification_invalid_and_revoked(test_users, db: Session):
    """
    AC09: Verifies report verification returns NOT_FOUND for unknown references
    and INVALID_OR_REVOKED for explicitly revoked reports.
    """
    # 1. Non-existent reference
    res_fake = client.get("/api/v1/reports/NON-EXISTENT-REF-999/verify")
    assert res_fake.status_code == 200
    data_fake = res_fake.json()
    assert data_fake["is_valid"] is False
    assert data_fake["status"] == "NOT_FOUND"

    # 2. Revoked report
    ref_revoked = "GNX-RPT-REVOKED-01"
    assess_revoked = Assessment(
        id="assess-revoked-uuid",
        user_id=1,
        session_token="token-revoked",
        questionnaire_version_id=1,
        status=AssessmentStatus.SUBMITTED
    )
    db.add(assess_revoked)

    report = AssessmentReport(
        report_reference=ref_revoked,
        assessment_id=assess_revoked.id,
        session_token="token-revoked",
        questionnaire_version_tag="v1.0.0",
        rule_engine_version="v1.0.0",
        outcome_tier=ClinicalOutcomeTier.TIER_1_NO_RISK,
        outcome_title_en="Routine Care",
        outcome_title_ar="عناية روتينية",
        outcome_description_en="Summary.",
        outcome_description_ar="ملخص.",
        clinical_disclaimer_en="Disclaimer.",
        clinical_disclaimer_ar="إخلاء مسؤولية."
    )
    db.add(report)

    # Add revocation audit entry
    revocation_log = AuditLog(
        user_id=1,
        action="REVOKE_REPORT_PUBLIC_ACCESS",
        resource_type="AssessmentReport",
        resource_id=ref_revoked,
        details={"reason": "patient requested revocation"},
        timestamp=datetime.now(timezone.utc)
    )
    db.add(revocation_log)
    db.commit()

    res_rev = client.get(f"/api/v1/reports/{ref_revoked}/verify")
    assert res_rev.status_code == 200
    data_rev = res_rev.json()
    assert data_rev["is_valid"] is False
    assert data_rev["status"] == "INVALID_OR_REVOKED"

# -----------------------------------------------------------------------------
# 4. Secure Report Sharing & Revocation Tests
# -----------------------------------------------------------------------------
def test_report_share_lifecycle_and_access(test_users, db: Session):
    """
    AC10: Verifies secure report sharing lifecycle:
    - Creation of expiring JWT share token with explicit patient consent
    - Access via GET /api/v1/reports/shared/{share_token}
    - PDF download via share_token
    - Revocation of token and subsequent access rejection (401)
    """
    u_a = test_users["user_a"]
    ref = "GNX-RPT-SHARE-01"

    assessment = Assessment(
        id="p13-share-assess-uuid",
        user_id=u_a.id,
        session_token="p13_share_token",
        questionnaire_version_id=1,
        status=AssessmentStatus.SUBMITTED
    )
    db.add(assessment)

    report = AssessmentReport(
        report_reference=ref,
        assessment_id=assessment.id,
        user_id=u_a.id,
        session_token=assessment.session_token,
        questionnaire_version_tag="v1.0.0",
        rule_engine_version="v1.0.0",
        outcome_tier=ClinicalOutcomeTier.TIER_2_RISK_FACTORS,
        outcome_title_en="Modifiable Risk Factors",
        outcome_title_ar="عوامل خطر قابلة للتعديل",
        outcome_description_en="Summary.",
        outcome_description_ar="ملخص.",
        clinical_disclaimer_en="Disclaimer.",
        clinical_disclaimer_ar="إخلاء مسؤولية."
    )
    db.add(report)
    db.commit()

    # Step 1: Patient A generates share token
    share_payload = {
        "clinician_email": "clinician@clinic.ae",
        "expires_in_days": 7
    }
    res_share = client.post(f"/api/v1/reports/{ref}/share", json=share_payload, headers=test_users["headers_a"])
    assert res_share.status_code == 200
    share_data = res_share.json()
    share_token = share_data["share_token"]
    assert share_token is not None
    assert share_data["status"] == "ACTIVE"

    # Step 2: Access shared report via share_token (no user auth needed, token serves as credential)
    res_view = client.get(f"/api/v1/reports/shared/{share_token}")
    assert res_view.status_code == 200
    assert res_view.json()["report_reference"] == ref

    # Step 3: Download PDF via share token
    res_pdf = client.get(f"/api/v1/reports/{ref}/download?share_token={share_token}")
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert res_pdf.content.startswith(b"%PDF-")

    # Step 4: Revoke share token
    res_revoke = client.post(f"/api/v1/reports/{ref}/revoke-share?share_token={share_token}", headers=test_users["headers_a"])
    assert res_revoke.status_code == 200
    assert res_revoke.json()["status"] == "revoked"

    # Step 5: Verify subsequent access is rejected (HTTP 401)
    res_view_revoked = client.get(f"/api/v1/reports/shared/{share_token}")
    assert res_view_revoked.status_code == 401
    assert "revoked" in res_view_revoked.json()["detail"].lower()

def test_report_share_idor_forbidden(test_users, db: Session):
    """
    AC11: Verifies that User B cannot share User A's report (IDOR Protection -> 403 Forbidden).
    """
    u_a = test_users["user_a"]
    ref = "GNX-RPT-USER-A-ONLY"

    assessment = Assessment(
        id="p13-assess-a-only-uuid",
        user_id=u_a.id,
        session_token="p13_a_only_token",
        questionnaire_version_id=1,
        status=AssessmentStatus.SUBMITTED
    )
    db.add(assessment)

    report = AssessmentReport(
        report_reference=ref,
        assessment_id=assessment.id,
        user_id=u_a.id,
        session_token=assessment.session_token,
        questionnaire_version_tag="v1.0.0",
        rule_engine_version="v1.0.0",
        outcome_tier=ClinicalOutcomeTier.TIER_1_NO_RISK,
        outcome_title_en="Routine Care",
        outcome_title_ar="عناية روتينية",
        outcome_description_en="Summary.",
        outcome_description_ar="ملخص.",
        clinical_disclaimer_en="Disclaimer.",
        clinical_disclaimer_ar="إخلاء مسؤولية."
    )
    db.add(report)
    db.commit()

    # User B attempts to share User A's report
    share_payload = {"expires_in_days": 3}
    res = client.post(f"/api/v1/reports/{ref}/share", json=share_payload, headers=test_users["headers_b"])
    assert res.status_code == 403
    assert "do not own" in res.json()["detail"].lower()

# -----------------------------------------------------------------------------
# 5. Historical Assessment Comparison Tests
# -----------------------------------------------------------------------------
def test_historical_assessment_comparison_success(test_users, db: Session):
    """
    AC12: Verifies safe historical assessment comparison.
    Calculates differences in reported risk factors, response choices, and recommended specialties.
    Includes mandatory non-diagnostic disclaimers.
    """
    u_a = test_users["user_a"]

    # Base assessment (earlier)
    assess_base = Assessment(
        id="p13-compare-base-uuid",
        user_id=u_a.id,
        session_token="compare_base_token",
        questionnaire_version_id=1,
        status=AssessmentStatus.SUBMITTED,
        started_at=datetime(2026, 1, 10, tzinfo=timezone.utc),
        submitted_at=datetime(2026, 1, 10, tzinfo=timezone.utc)
    )
    db.add(assess_base)

    report_base = AssessmentReport(
        report_reference="GNX-RPT-COMPARE-BASE",
        assessment_id=assess_base.id,
        user_id=u_a.id,
        session_token=assess_base.session_token,
        questionnaire_version_tag="v1.0.0",
        rule_engine_version="v1.0.0",
        outcome_tier=ClinicalOutcomeTier.TIER_2_RISK_FACTORS,
        outcome_title_en="Lifestyle Factors",
        outcome_title_ar="عوامل نمط الحياة",
        outcome_description_en="Base summary.",
        outcome_description_ar="ملخص الأساس.",
        recommended_specialties=["General Practitioner"],
        identified_risk_factors_json=[
            {"factor_code": "SMOKING", "title_en": "Tobacco Use"}
        ],
        responses_summary_json=[
            {"question_key": "q_smoking", "prompt_en": "Do you smoke?", "answer_display_en": "Daily"}
        ],
        clinical_disclaimer_en="Disclaimer.",
        clinical_disclaimer_ar="إخلاء مسؤولية."
    )
    db.add(report_base)

    # Target assessment (later)
    assess_target = Assessment(
        id="p13-compare-target-uuid",
        user_id=u_a.id,
        session_token="compare_target_token",
        questionnaire_version_id=1,
        status=AssessmentStatus.SUBMITTED,
        started_at=datetime(2026, 4, 15, tzinfo=timezone.utc),
        submitted_at=datetime(2026, 4, 15, tzinfo=timezone.utc)
    )
    db.add(assess_target)

    report_target = AssessmentReport(
        report_reference="GNX-RPT-COMPARE-TARGET",
        assessment_id=assess_target.id,
        user_id=u_a.id,
        session_token=assess_target.session_token,
        questionnaire_version_tag="v1.0.0",
        rule_engine_version="v1.0.0",
        outcome_tier=ClinicalOutcomeTier.TIER_3_EVAL_RECOMMENDED,
        outcome_title_en="Clinical Evaluation Recommended",
        outcome_title_ar="يوصى بالتقييم الإكلينيكي",
        outcome_description_en="Target summary.",
        outcome_description_ar="ملخص الهدف.",
        recommended_specialties=["Male Reproductive Urologist / Andrologist"],
        identified_risk_factors_json=[
            {"factor_code": "VARICOCELE_SUSPECTED", "title_en": "Scrotal Swelling"}
        ],
        responses_summary_json=[
            {"question_key": "q_smoking", "prompt_en": "Do you smoke?", "answer_display_en": "Quit / Non-smoker"},
            {"question_key": "q_scrotal_mass", "prompt_en": "Scrotal swelling?", "answer_display_en": "Yes, left side"}
        ],
        clinical_disclaimer_en="Disclaimer.",
        clinical_disclaimer_ar="إخلاء مسؤولية."
    )
    db.add(report_target)
    db.commit()

    res = client.get(
        f"/api/v1/assessments/compare?base_id={assess_base.id}&target_id={assess_target.id}",
        headers=test_users["headers_a"]
    )
    assert res.status_code == 200
    comp = res.json()

    assert comp["outcome_changed"] is True
    assert comp["base_outcome_tier"] in ("TIER_2_RISK_FACTORS", "RISK_FACTORS_IDENTIFIED")
    assert comp["target_outcome_tier"] in ("TIER_3_EVAL_RECOMMENDED", "CLINICAL_EVALUATION_RECOMMENDED")

    # New risk factor in target
    assert any(f["factor_code"] == "VARICOCELE_SUSPECTED" for f in comp["new_risk_factors"])
    # Resolved risk factor from base
    assert any(f["factor_code"] == "SMOKING" for f in comp["resolved_risk_factors"])

    # Response change in smoking question
    assert any(r["question_key"] == "q_smoking" for r in comp["response_changes"])

    # Specialties differential
    assert "Male Reproductive Urologist / Andrologist" in comp["specialties_diff"]["added_specialties"]

    # Mandatory non-diagnostic disclaimers
    assert "NOT be interpreted as biological progression" in comp["disclaimer_en"]
    assert "لا يجوز بأي حال تفسيرها كتطور بيولوجي" in comp["disclaimer_ar"]

def test_historical_assessment_comparison_idor_forbidden(test_users, db: Session):
    """
    AC13: Verifies that comparing assessments belonging to another user is rejected.
    """
    u_a = test_users["user_a"]
    u_b = test_users["user_b"]

    a_a = Assessment(
        id="p13-comp-idor-a",
        user_id=u_a.id,
        session_token="comp_idor_a_tok",
        questionnaire_version_id=1,
        status=AssessmentStatus.SUBMITTED
    )
    a_b = Assessment(
        id="p13-comp-idor-b",
        user_id=u_b.id,
        session_token="comp_idor_b_tok",
        questionnaire_version_id=1,
        status=AssessmentStatus.SUBMITTED
    )
    db.add_all([a_a, a_b])
    db.commit()

    # User B attempts to compare User A's assessment
    res = client.get(
        f"/api/v1/assessments/compare?base_id={a_a.id}&target_id={a_b.id}",
        headers=test_users["headers_b"]
    )
    assert res.status_code in (403, 404)
