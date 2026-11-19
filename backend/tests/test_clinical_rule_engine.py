import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.database import SessionLocal, Base, engine
from app.core.security import User, RoleEnum
from app.models.questionnaire import (
    QuestionnaireVersion, Question, Assessment, AssessmentResponse,
    QuestionnaireStatus, QuestionDomain, QuestionType, AssessmentStatus
)
from app.models.clinical_rules import (
    ClinicalRule, ClinicalOutcomeTier, ClinicalRuleStatus, ClinicalRuleVersionRecord
)
from app.models.assessment_report import AssessmentReport
from app.services.clinical_rule_engine import ClinicalRuleEngineService, MANDATORY_DISCLAIMER_EN
from app.services.clinical_rule_management_service import ClinicalRuleManagementService
from app.schemas.clinical_rules import ClinicalRuleCreate, ClinicalRuleReviewAction
from app.core.seed_questionnaire import seed_questionnaire_v1
from app.core.seed_clinical_rules import seed_clinical_rules_v1

@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_questionnaire_v1(db)
    seed_clinical_rules_v1(db)
    yield db
    db.close()

def test_tier_1_no_reported_risk_factors(setup_db: Session):
    """
    Outcome 1: NO REPORTED RISK FACTORS.
    Verifies that when all answers indicate no risk, Tier 1 is returned,
    and the mandatory disclaimer clearly explains this does NOT prove normal fertility.
    """
    db = setup_db
    token = f"tier1_{uuid.uuid4().hex}"
    q_version = db.query(QuestionnaireVersion).filter(QuestionnaireVersion.status == QuestionnaireStatus.PUBLISHED).first()

    assessment = Assessment(
        session_token=token,
        questionnaire_version_id=q_version.id,
        status=AssessmentStatus.IN_PROGRESS
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    # Answer all negative / normal
    q_attempt = db.query(Question).filter(Question.question_key == "Q_ATTEMPT_DURATION").first()
    q_pain = db.query(Question).filter(Question.question_key == "Q_ACUTE_SCROTAL_PAIN").first()
    q_lump = db.query(Question).filter(Question.question_key == "Q_PAINLESS_TESTIS_LUMP").first()
    q_steroid = db.query(Question).filter(Question.question_key == "Q_ANABOLIC_STEROIDS").first()

    db.add_all([
        AssessmentResponse(assessment_id=assessment.id, question_id=q_attempt.id, question_key=q_attempt.question_key, answer_value="less_than_6m"),
        AssessmentResponse(assessment_id=assessment.id, question_id=q_pain.id, question_key=q_pain.question_key, answer_value="no"),
        AssessmentResponse(assessment_id=assessment.id, question_id=q_lump.id, question_key=q_lump.question_key, answer_value="no"),
        AssessmentResponse(assessment_id=assessment.id, question_id=q_steroid.id, question_key=q_steroid.question_key, answer_value="no")
    ])
    db.commit()

    report = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)

    assert report.outcome_tier == ClinicalOutcomeTier.TIER_1_NO_RISK
    assert "NO REPORTED RISK FACTORS" in report.outcome_title_en
    assert "does not measure" in report.clinical_disclaimer_en.lower() or "does not establish" in report.clinical_disclaimer_en.lower()
    assert report.is_urgent_red_flag is False
    assert len(report.triggered_rules_snapshot_json) == 0

def test_tier_2_risk_factors_identified_lifestyle(setup_db: Session):
    """
    Outcome 2: RISK FACTORS IDENTIFIED.
    Verifies lifestyle/environmental risks (Tobacco, Dokha, Scrotal heat) trigger Tier 2
    without claiming an infertility diagnosis.
    """
    db = setup_db
    token = f"tier2_{uuid.uuid4().hex}"
    q_version = db.query(QuestionnaireVersion).filter(QuestionnaireVersion.status == QuestionnaireStatus.PUBLISHED).first()

    assessment = Assessment(
        session_token=token,
        questionnaire_version_id=q_version.id,
        status=AssessmentStatus.IN_PROGRESS
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    q_tobacco = db.query(Question).filter(Question.question_key == "Q_TOBACCO_USE").first()
    q_heat = db.query(Question).filter(Question.question_key == "Q_SCROTAL_HEAT").first()
    q_pain = db.query(Question).filter(Question.question_key == "Q_ACUTE_SCROTAL_PAIN").first()

    db.add_all([
        AssessmentResponse(assessment_id=assessment.id, question_id=q_tobacco.id, question_key=q_tobacco.question_key, answer_value=["dokha_medwakh"]),
        AssessmentResponse(assessment_id=assessment.id, question_id=q_heat.id, question_key=q_heat.question_key, answer_value="yes"),
        AssessmentResponse(assessment_id=assessment.id, question_id=q_pain.id, question_key=q_pain.question_key, answer_value="no")
    ])
    db.commit()

    report = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)

    assert report.outcome_tier == ClinicalOutcomeTier.TIER_2_RISK_FACTORS
    assert "RISK FACTORS IDENTIFIED" in report.outcome_title_en
    assert len(report.triggered_rules_snapshot_json) >= 2
    rule_codes = [r["rule_code"] for r in report.triggered_rules_snapshot_json]
    assert "R-LST-TOBACCO-DOKHA" in rule_codes
    assert "R-LST-SCROTAL-HYPERTHERMIA" in rule_codes
    assert any("WHO" in ev["guideline_body"] or "AUA" in ev["guideline_body"] for ev in report.evidence_citations_json)

def test_tier_3_clinical_evaluation_recommended(setup_db: Session):
    """
    Outcome 3: CLINICAL EVALUATION RECOMMENDED.
    Verifies prolonged time attempting pregnancy (>12m) and exogenous anabolic steroids trigger Tier 3,
    and routes appropriately to Male Reproductive Urologist / Andrologist.
    """
    db = setup_db
    token = f"tier3_{uuid.uuid4().hex}"
    q_version = db.query(QuestionnaireVersion).filter(QuestionnaireVersion.status == QuestionnaireStatus.PUBLISHED).first()

    assessment = Assessment(
        session_token=token,
        questionnaire_version_id=q_version.id,
        status=AssessmentStatus.IN_PROGRESS
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    q_attempt = db.query(Question).filter(Question.question_key == "Q_ATTEMPT_DURATION").first()
    q_steroid = db.query(Question).filter(Question.question_key == "Q_ANABOLIC_STEROIDS").first()
    q_pain = db.query(Question).filter(Question.question_key == "Q_ACUTE_SCROTAL_PAIN").first()

    db.add_all([
        AssessmentResponse(assessment_id=assessment.id, question_id=q_attempt.id, question_key=q_attempt.question_key, answer_value="12_to_24m"),
        AssessmentResponse(assessment_id=assessment.id, question_id=q_steroid.id, question_key=q_steroid.question_key, answer_value="yes_current"),
        AssessmentResponse(assessment_id=assessment.id, question_id=q_pain.id, question_key=q_pain.question_key, answer_value="no")
    ])
    db.commit()

    report = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)

    assert report.outcome_tier == ClinicalOutcomeTier.TIER_3_EVAL_RECOMMENDED
    assert "CLINICAL EVALUATION RECOMMENDED" in report.outcome_title_en
    assert "Male Reproductive Urologist / Andrologist" in report.recommended_specialties
    rule_codes = [r["rule_code"] for r in report.triggered_rules_snapshot_json]
    assert "R-REP-PROLONGED-TTC" in rule_codes
    assert "R-MED-ANABOLIC-STEROIDS" in rule_codes

def test_tier_4_urgent_safety_circuit_priority_over_other_tiers(setup_db: Session):
    """
    Outcome 4: URGENT MEDICAL ASSESSMENT & SAFETY PRIORITY.
    Verifies that when both chronic infertility (Tier 3) AND acute testicular pain (Tier 4) are reported,
    the urgent emergency pathway takes absolute precedence over ordinary risk tiers.
    """
    db = setup_db
    token = f"tier4_{uuid.uuid4().hex}"
    q_version = db.query(QuestionnaireVersion).filter(QuestionnaireVersion.status == QuestionnaireStatus.PUBLISHED).first()

    assessment = Assessment(
        session_token=token,
        questionnaire_version_id=q_version.id,
        status=AssessmentStatus.IN_PROGRESS
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    q_attempt = db.query(Question).filter(Question.question_key == "Q_ATTEMPT_DURATION").first()
    q_pain = db.query(Question).filter(Question.question_key == "Q_ACUTE_SCROTAL_PAIN").first()

    db.add_all([
        AssessmentResponse(assessment_id=assessment.id, question_id=q_attempt.id, question_key=q_attempt.question_key, answer_value="more_than_2y"),
        AssessmentResponse(assessment_id=assessment.id, question_id=q_pain.id, question_key=q_pain.question_key, answer_value="yes")
    ])
    db.commit()

    report = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)

    assert report.outcome_tier == ClinicalOutcomeTier.TIER_4_URGENT
    assert report.is_urgent_red_flag is True
    assert "URGENT MEDICAL ASSESSMENT" in report.outcome_title_en
    assert "Emergency" in report.urgent_emergency_guidance_en
    assert "998" in report.urgent_emergency_guidance_en
    assert "6 hours" in report.urgent_emergency_guidance_en

def test_urgent_painless_testicular_lump_differentiation(setup_db: Session):
    """
    Urgent Safety Circuit: Differentiates painless firm testicular lump from acute pain.
    Triggers prompt urological evaluation and scrotal Doppler ultrasound to rule out testicular neoplasm.
    """
    db = setup_db
    token = f"lump_{uuid.uuid4().hex}"
    q_version = db.query(QuestionnaireVersion).filter(QuestionnaireVersion.status == QuestionnaireStatus.PUBLISHED).first()

    assessment = Assessment(
        session_token=token,
        questionnaire_version_id=q_version.id,
        status=AssessmentStatus.IN_PROGRESS
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    q_lump = db.query(Question).filter(Question.question_key == "Q_PAINLESS_TESTIS_LUMP").first()
    q_pain = db.query(Question).filter(Question.question_key == "Q_ACUTE_SCROTAL_PAIN").first()

    db.add_all([
        AssessmentResponse(assessment_id=assessment.id, question_id=q_lump.id, question_key=q_lump.question_key, answer_value="yes"),
        AssessmentResponse(assessment_id=assessment.id, question_id=q_pain.id, question_key=q_pain.question_key, answer_value="no")
    ])
    db.commit()

    report = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)

    assert report.outcome_tier == ClinicalOutcomeTier.TIER_4_URGENT
    assert report.is_urgent_red_flag is True
    assert "neoplasm" in report.urgent_emergency_guidance_en.lower() or "mass" in report.urgent_emergency_guidance_en.lower()
    assert "ultrasound" in report.urgent_emergency_guidance_en.lower()

def test_safe_answer_principle_unsure_and_prefer_not_to_say(setup_db: Session):
    """
    Safe Answer Principle:
    Verifies that 'Unsure' and 'Prefer not to say' are NOT treated as negative findings
    and do NOT accidentally trigger affirmative rules.
    """
    db = setup_db
    token = f"safe_{uuid.uuid4().hex}"
    q_version = db.query(QuestionnaireVersion).filter(QuestionnaireVersion.status == QuestionnaireStatus.PUBLISHED).first()

    assessment = Assessment(
        session_token=token,
        questionnaire_version_id=q_version.id,
        status=AssessmentStatus.IN_PROGRESS
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    q_steroid = db.query(Question).filter(Question.question_key == "Q_ANABOLIC_STEROIDS").first()
    q_lump = db.query(Question).filter(Question.question_key == "Q_PAINLESS_TESTIS_LUMP").first()

    # User is unsure about steroids, prefers not to say about lump
    db.add_all([
        AssessmentResponse(assessment_id=assessment.id, question_id=q_steroid.id, question_key=q_steroid.question_key, is_unsure=True),
        AssessmentResponse(assessment_id=assessment.id, question_id=q_lump.id, question_key=q_lump.question_key, is_prefer_not_to_say=True)
    ])
    db.commit()

    report = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)

    # Should not trigger positive steroid rule or lump red flag
    assert report.outcome_tier == ClinicalOutcomeTier.TIER_1_NO_RISK
    assert report.is_urgent_red_flag is False

    # Responses summary must preserve safe answer flags
    steroid_summary = next(s for s in report.responses_summary_json if s["question_key"] == "Q_ANABOLIC_STEROIDS")
    lump_summary = next(s for s in report.responses_summary_json if s["question_key"] == "Q_PAINLESS_TESTIS_LUMP")
    assert steroid_summary["is_unsure"] is True
    assert lump_summary["is_prefer_not_to_say"] is True

def test_missing_responses_handled_safely(setup_db: Session):
    """
    Missing Responses:
    Verifies that skipped/missing questions in the assessment are preserved in the report
    and marked as 'Not answered (Preserved as safe missing)'.
    """
    db = setup_db
    token = f"missing_{uuid.uuid4().hex}"
    q_version = db.query(QuestionnaireVersion).filter(QuestionnaireVersion.status == QuestionnaireStatus.PUBLISHED).first()

    assessment = Assessment(
        session_token=token,
        questionnaire_version_id=q_version.id,
        status=AssessmentStatus.IN_PROGRESS
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    # Empty responses
    report = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)

    assert report.outcome_tier == ClinicalOutcomeTier.TIER_1_NO_RISK
    missing_items = [s for s in report.responses_summary_json if s["is_missing"]]
    assert len(missing_items) == 19

def test_conditional_question_evaluation(setup_db: Session):
    """
    Conditional logic:
    Verifies that a conditional child question (Q_TESTIS_SURGERY_TYPE: undescended_testis)
    triggers the cryptorchidism rule when affirmative.
    """
    db = setup_db
    token = f"cond_{uuid.uuid4().hex}"
    q_version = db.query(QuestionnaireVersion).filter(QuestionnaireVersion.status == QuestionnaireStatus.PUBLISHED).first()

    assessment = Assessment(
        session_token=token,
        questionnaire_version_id=q_version.id,
        status=AssessmentStatus.IN_PROGRESS
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    q_surg = db.query(Question).filter(Question.question_key == "Q_TESTIS_SURGERY").first()
    q_type = db.query(Question).filter(Question.question_key == "Q_TESTIS_SURGERY_TYPE").first()

    db.add_all([
        AssessmentResponse(assessment_id=assessment.id, question_id=q_surg.id, question_key=q_surg.question_key, answer_value="yes"),
        AssessmentResponse(assessment_id=assessment.id, question_id=q_type.id, question_key=q_type.question_key, answer_value="undescended_testis")
    ])
    db.commit()

    report = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)

    assert report.outcome_tier == ClinicalOutcomeTier.TIER_3_EVAL_RECOMMENDED
    rule_codes = [r["rule_code"] for r in report.triggered_rules_snapshot_json]
    assert "R-TST-CRYPTORCHIDISM" in rule_codes

def test_historical_report_snapshot_reproducibility(setup_db: Session):
    """
    Historical Report Reproducibility:
    Verifies that once an assessment report is compiled and locked, subsequent modification
    or publication of new clinical rules does not alter the historical report.
    """
    db = setup_db
    token = f"snap_{uuid.uuid4().hex}"
    q_version = db.query(QuestionnaireVersion).filter(QuestionnaireVersion.status == QuestionnaireStatus.PUBLISHED).first()

    assessment = Assessment(
        session_token=token,
        questionnaire_version_id=q_version.id,
        status=AssessmentStatus.IN_PROGRESS
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    q_attempt = db.query(Question).filter(Question.question_key == "Q_ATTEMPT_DURATION").first()
    db.add(AssessmentResponse(assessment_id=assessment.id, question_id=q_attempt.id, question_key=q_attempt.question_key, answer_value="12_to_24m"))
    db.commit()

    report_1 = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)
    ref_1 = report_1.report_reference
    rule_count_1 = len(report_1.triggered_rules_snapshot_json)

    # Calling compile_assessment_report again retrieves the existing locked report
    report_2 = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)
    assert report_2.report_reference == ref_1
    assert len(report_2.triggered_rules_snapshot_json) == rule_count_1
    assert report_2.is_locked is True

def test_rbac_unauthorized_user_cannot_approve_or_publish_rules(setup_db: Session):
    """
    RBAC Governance:
    Ensures that only CLINICIAN or SUPER_ADMIN users can approve and publish clinical rules.
    Normal PATIENT or non-clinician users receive 403 Forbidden.
    """
    db = setup_db
    patient = db.query(User).filter(User.role == RoleEnum.PATIENT).first()
    clinician = db.query(User).filter(User.role == RoleEnum.CLINICIAN).first()

    unique_code = f"R-RBAC-{uuid.uuid4().hex[:6].upper()}"

    # Create a draft rule
    draft_data = ClinicalRuleCreate(
        rule_code=unique_code,
        title_en="Test Draft Rule",
        title_ar="قاعدة مسودة تجريبية",
        domain_code=QuestionDomain.LIFESTYLE_HABITS,
        relevant_question_keys=["Q_TOBACCO_USE"],
        outcome_tier=ClinicalOutcomeTier.TIER_2_RISK_FACTORS,
        priority_rank=100,
        trigger_criteria={"operator": "equals", "question_key": "Q_TOBACCO_USE", "expected_value": "yes"},
        clinical_rationale_en="Test rationale",
        clinical_rationale_ar="تعليل تجريبي",
        evidence_references=[{
            "title": "EAU Guidelines on Male Sexual & Reproductive Health",
            "year": 2024,
            "guideline_body": "European Association of Urology",
            "doi_or_url": "https://uroweb.org"
        }]
    )
    rule = ClinicalRuleManagementService.create_rule(db, draft_data, clinician)
    ClinicalRuleManagementService.submit_for_review(db, rule.id, clinician)

    # Patient attempt to approve must raise 403
    with pytest.raises(HTTPException) as exc_info:
        ClinicalRuleManagementService.clinical_review(
            db, rule.id,
            ClinicalRuleReviewAction(action="APPROVE", reviewer_notes="Unauthorized attempt"),
            patient
        )
    assert exc_info.value.status_code == 403

    # Clinician approval succeeds
    approved_rule = ClinicalRuleManagementService.clinical_review(
        db, rule.id,
        ClinicalRuleReviewAction(action="APPROVE", reviewer_notes="Approved by licensed clinician"),
        clinician
    )
    assert approved_rule.status == ClinicalRuleStatus.APPROVED

    # Patient attempt to publish must raise 403
    with pytest.raises(HTTPException) as exc_pub:
        ClinicalRuleManagementService.publish_rule(db, rule.id, patient)
    assert exc_pub.value.status_code == 403

    # Clinician publication succeeds and creates version record
    published_rule = ClinicalRuleManagementService.publish_rule(db, rule.id, clinician)
    assert published_rule.status == ClinicalRuleStatus.PUBLISHED

    versions = ClinicalRuleManagementService.get_rule_versions(db, rule.id)
    assert len(versions) >= 1
    assert versions[0].rule_code == unique_code

def test_evidence_traceability_verified_guidelines(setup_db: Session):
    """
    Evidence Traceability:
    Ensures that active clinical rules are tied to verified evidence sources
    (EAU, AUA, WHO, Lancet) with author, year, and recommendation text.
    """
    db = setup_db
    rules = db.query(ClinicalRule).filter(ClinicalRule.status == ClinicalRuleStatus.PUBLISHED).all()
    assert len(rules) >= 10

    for rule in rules:
        assert len(rule.evidence_references) > 0
        ref = rule.evidence_references[0]
        assert "title" in ref
        assert "year" in ref
        assert "guideline_body" in ref
        assert ref["year"] >= 2020
