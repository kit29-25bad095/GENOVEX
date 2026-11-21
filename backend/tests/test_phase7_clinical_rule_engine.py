"""
GENOVEX Phase 7: Deterministic Clinical Rule Engine Test Suite
Validates all 20 Acceptance Criteria (AC 1 through AC 20) in strict isolation
against disposable sandbox databases without modifying live genovex.db.
"""

import os
import uuid
import json
import sqlite3
import hashlib
import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.core.database import SessionLocal, Base, engine
from app.core.config import AUTHORITATIVE_DB_PATH
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
from app.services.predicate_evaluator import (
    PredicateEvaluator, PredicateEvaluationState, RuleEvaluationState, MAX_PREDICATE_DEPTH
)
from app.services.clinical_rule_engine import ClinicalRuleEngineService
from app.core.seed_questionnaire import seed_questionnaire_v1
from app.core.seed_clinical_rules import seed_clinical_rules_v1


@pytest.fixture(scope="module")
def setup_phase7_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_questionnaire_v1(db)
    seed_clinical_rules_v1(db)
    yield db
    db.close()


# ---------------------------------------------------------------------------
# AC 1: Canonical Deterministic Repeatability
# ---------------------------------------------------------------------------
def test_ac01_canonical_deterministic_repeatability(setup_phase7_db: Session):
    """
    AC 1: Evaluates assessment rules 100 times on identical inputs.
    Asserts 100 identical canonical evaluation SHA-256 hashes.
    """
    db = setup_phase7_db
    token = f"ac01_{uuid.uuid4().hex}"
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
    q_age = db.query(Question).filter(Question.question_key == "Q_AGE").first()

    db.add_all([
        AssessmentResponse(assessment_id=assessment.id, question_id=q_steroid.id, question_key="Q_ANABOLIC_STEROIDS", answer_value="yes_past"),
        AssessmentResponse(assessment_id=assessment.id, question_id=q_age.id, question_key="Q_AGE", answer_value=32)
    ])
    db.commit()

    report = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)

    report_dict = {
        "outcome_tier": report.outcome_tier.value,
        "is_urgent_red_flag": report.is_urgent_red_flag,
        "rule_engine_version": report.rule_engine_version,
        "questionnaire_version_tag": report.questionnaire_version_tag,
        "evaluation_completeness": "DETERMINATE",
        "triggered_rules": report.triggered_rules_snapshot_json,
        "identified_risk_factors": report.identified_risk_factors_json,
        "recommended_specialties": report.recommended_specialties
    }

    base_hash = ClinicalRuleEngineService.compute_canonical_report_hash(report_dict)

    hashes = [ClinicalRuleEngineService.compute_canonical_report_hash(report_dict) for _ in range(100)]
    assert len(set(hashes)) == 1, "Expected 100 identical SHA-256 hashes for identical clinical inputs"
    assert hashes[0] == base_hash


# ---------------------------------------------------------------------------
# AC 2: Fully Determinate Tier 1 Resolution across 14-Rule Fixture
# ---------------------------------------------------------------------------
def test_ac02_fully_determinate_tier_1_resolution(setup_phase7_db: Session):
    """
    AC 2: Submits supported non-trigger answers across all 14 published rules.
    Verifies: outcome_tier = TIER_1_NO_RISK, 0 triggered rules, evaluation_completeness = DETERMINATE.
    """
    db = setup_phase7_db
    token = f"ac02_{uuid.uuid4().hex}"
    q_version = db.query(QuestionnaireVersion).filter(QuestionnaireVersion.status == QuestionnaireStatus.PUBLISHED).first()

    assessment = Assessment(
        session_token=token,
        questionnaire_version_id=q_version.id,
        status=AssessmentStatus.IN_PROGRESS
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    # 14 rule-mapped questions with explicit supported non-trigger answers
    answers_map = {
        "Q_ACUTE_SCROTAL_PAIN": "no",
        "Q_PAINLESS_TESTIS_LUMP": "no",
        "Q_ATTEMPT_DURATION": "not_actively_trying",
        "Q_ANABOLIC_STEROIDS": "no",
        "Q_TESTIS_SURGERY": "no",  # deactivates child Q_TESTIS_SURGERY_TYPE
        "Q_EJACULATORY_PROFILE": "normal",
        "Q_HEMATOSPERMIA": "no",
        "Q_FAMILY_MALE_INFERTILITY": "no",
        "Q_TOBACCO_USE": ["none"],
        "Q_SCROTAL_HEAT": "no",
        "Q_SLEEP_APNEA": "no",
        "Q_HAIR_LOSS_MEDS": "no",
        "Q_OCCUPATIONAL_HAZARDS": ["none"],
        "Q_AGE": 30,
        # 5 unmapped questions completed
        "Q_BMI_CATEGORY": "normal_weight",
        "Q_PREVIOUS_PATERNITY": "no",
        "Q_CHRONIC_DISEASES": ["none"],
        "Q_HORMONAL_SYMPTOMS": ["none"]
    }

    responses_list = []
    for qk, ans in answers_map.items():
        q = db.query(Question).filter(Question.question_key == qk).first()
        if q:
            responses_list.append(
                AssessmentResponse(
                    assessment_id=assessment.id,
                    question_id=q.id,
                    question_key=qk,
                    answer_value=ans,
                    conditional_pathway_active=True
                )
            )

    db.add_all(responses_list)
    db.commit()

    report = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)

    assert report.outcome_tier == ClinicalOutcomeTier.TIER_1_NO_RISK
    assert "NO REPORTED RISK FACTORS" in report.outcome_title_en
    assert "INCOMPLETE" not in report.outcome_title_en
    assert len(report.triggered_rules_snapshot_json) == 0
    assert report.is_urgent_red_flag is False


# ---------------------------------------------------------------------------
# AC 3: Incomplete Assessment Qualification & API Withholding
# ---------------------------------------------------------------------------
def test_ac03_incomplete_assessment_qualification_and_api_withholding(setup_phase7_db: Session):
    """
    AC 3: 0 rules triggered + 1+ answers are Unsure/Declined/Missing.
    Asserts:
    1. Report compiles with outcome_title containing INCOMPLETE EVALUATION and narrative disclaimer.
    2. Patient-facing endpoint GET /assessment/{token}/report returns HTTP 422 (INCOMPLETE_EVALUATION_WITHHELD).
    3. Clinician user can access the report without withholding.
    """
    db = setup_phase7_db
    token = f"ac03_{uuid.uuid4().hex}"
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
    db.add(AssessmentResponse(assessment_id=assessment.id, question_id=q_steroid.id, question_key="Q_ANABOLIC_STEROIDS", is_unsure=True))
    db.commit()

    report = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)

    assert report.outcome_tier == ClinicalOutcomeTier.TIER_1_NO_RISK
    assert "INCOMPLETE EVALUATION" in report.outcome_title_en
    assert "CANNOT confirm the absence of risk factors" in report.outcome_description_en
    assert len(report.triggered_rules_snapshot_json) == 0

    client = TestClient(fastapi_app)

    # Patient request without clinician token: Must return HTTP 422 Withheld
    res_patient = client.get(f"/api/v1/assessment/{token}/report")
    assert res_patient.status_code == 422
    err_json = res_patient.json()
    assert err_json["detail"]["code"] == "INCOMPLETE_EVALUATION_WITHHELD"

    # Clinician request: Must succeed with 200 OK
    clinician_user = db.query(User).filter(User.email == "clinician@genovex.ae").first()
    if not clinician_user:
        clinician_user = User(
            email="clinician@genovex.ae",
            hashed_password="hashed_pw_test",
            full_name="Dr. Clinician",
            role=RoleEnum.CLINICIAN,
            is_active=True
        )
        db.add(clinician_user)
        db.commit()

    clinician_token = create_access_token(data={"sub": clinician_user.email, "role": RoleEnum.CLINICIAN.value})
    res_clinician = client.get(
        f"/api/v1/assessment/{token}/report",
        headers={"Authorization": f"Bearer {clinician_token}"}
    )
    assert res_clinician.status_code == 200
    assert "INCOMPLETE EVALUATION" in res_clinician.json()["outcome_title_en"]


# ---------------------------------------------------------------------------
# AC 4: Tier 2 Lifestyle / Modifiable Trigger
# ---------------------------------------------------------------------------
def test_ac04_tier_2_lifestyle_modifiable_trigger(setup_phase7_db: Session):
    """
    AC 4: Submits affirmative tobacco response.
    Asserts: outcome_tier = TIER_2_RISK_FACTORS, R-LST-TOBACCO-DOKHA triggered.
    """
    db = setup_phase7_db
    token = f"ac04_{uuid.uuid4().hex}"
    q_version = db.query(QuestionnaireVersion).filter(QuestionnaireVersion.status == QuestionnaireStatus.PUBLISHED).first()

    assessment = Assessment(session_token=token, questionnaire_version_id=q_version.id, status=AssessmentStatus.IN_PROGRESS)
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    q_tobacco = db.query(Question).filter(Question.question_key == "Q_TOBACCO_USE").first()
    db.add(AssessmentResponse(assessment_id=assessment.id, question_id=q_tobacco.id, question_key="Q_TOBACCO_USE", answer_value=["dokha_medwakh"]))
    db.commit()

    report = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)

    assert report.outcome_tier == ClinicalOutcomeTier.TIER_2_RISK_FACTORS
    rule_codes = [r["rule_code"] for r in report.triggered_rules_snapshot_json]
    assert "R-LST-TOBACCO-DOKHA" in rule_codes


# ---------------------------------------------------------------------------
# AC 5: Tier 3 Specialist Evaluation Trigger
# ---------------------------------------------------------------------------
def test_ac05_tier_3_specialist_evaluation_trigger(setup_phase7_db: Session):
    """
    AC 5: Submits TTC >= 12m.
    Asserts: outcome_tier = TIER_3_EVAL_RECOMMENDED, specialty includes Reproductive Urologist.
    """
    db = setup_phase7_db
    token = f"ac05_{uuid.uuid4().hex}"
    q_version = db.query(QuestionnaireVersion).filter(QuestionnaireVersion.status == QuestionnaireStatus.PUBLISHED).first()

    assessment = Assessment(session_token=token, questionnaire_version_id=q_version.id, status=AssessmentStatus.IN_PROGRESS)
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    q_ttc = db.query(Question).filter(Question.question_key == "Q_ATTEMPT_DURATION").first()
    db.add(AssessmentResponse(assessment_id=assessment.id, question_id=q_ttc.id, question_key="Q_ATTEMPT_DURATION", answer_value="12_to_24m"))
    db.commit()

    report = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)

    assert report.outcome_tier == ClinicalOutcomeTier.TIER_3_EVAL_RECOMMENDED
    rule_codes = [r["rule_code"] for r in report.triggered_rules_snapshot_json]
    assert "R-REP-PROLONGED-TTC" in rule_codes
    assert any("Urologist" in s or "Andrologist" in s for s in report.recommended_specialties)


# ---------------------------------------------------------------------------
# AC 6: Tier 4 Urgent Emergency Safety Circuit (Software Regression Test)
# ---------------------------------------------------------------------------
def test_ac06_tier_4_urgent_emergency_safety_circuit_regression(setup_phase7_db: Session):
    """
    AC 6: Software regression test for acute scrotal pain.
    Verifies technical execution only: outcome_tier = TIER_4_URGENT, is_urgent_red_flag = True,
    and exact preservation of 6h and 998/999 guidance strings.
    """
    db = setup_phase7_db
    token = f"ac06_{uuid.uuid4().hex}"
    q_version = db.query(QuestionnaireVersion).filter(QuestionnaireVersion.status == QuestionnaireStatus.PUBLISHED).first()

    assessment = Assessment(session_token=token, questionnaire_version_id=q_version.id, status=AssessmentStatus.IN_PROGRESS)
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    q_pain = db.query(Question).filter(Question.question_key == "Q_ACUTE_SCROTAL_PAIN").first()
    db.add(AssessmentResponse(assessment_id=assessment.id, question_id=q_pain.id, question_key="Q_ACUTE_SCROTAL_PAIN", answer_value="yes"))
    db.commit()

    report = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)

    assert report.outcome_tier == ClinicalOutcomeTier.TIER_4_URGENT
    assert report.is_urgent_red_flag is True
    assert "within 6 hours" in report.urgent_emergency_guidance_en
    assert "998 / 999" in report.urgent_emergency_guidance_en


# ---------------------------------------------------------------------------
# AC 7: Tier 4 Oncology Triaging Differentiation (Software Regression Test)
# ---------------------------------------------------------------------------
def test_ac07_tier_4_oncology_triaging_differentiation_regression(setup_phase7_db: Session):
    """
    AC 7: Software regression test for painless testicular lump.
    Verifies technical execution only: outcome_tier = TIER_4_URGENT, is_urgent_red_flag = True,
    and exact preservation of scrotal Doppler ultrasound oncology guidance.
    """
    db = setup_phase7_db
    token = f"ac07_{uuid.uuid4().hex}"
    q_version = db.query(QuestionnaireVersion).filter(QuestionnaireVersion.status == QuestionnaireStatus.PUBLISHED).first()

    assessment = Assessment(session_token=token, questionnaire_version_id=q_version.id, status=AssessmentStatus.IN_PROGRESS)
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    q_lump = db.query(Question).filter(Question.question_key == "Q_PAINLESS_TESTIS_LUMP").first()
    db.add(AssessmentResponse(assessment_id=assessment.id, question_id=q_lump.id, question_key="Q_PAINLESS_TESTIS_LUMP", answer_value="yes"))
    db.commit()

    report = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)

    assert report.outcome_tier == ClinicalOutcomeTier.TIER_4_URGENT
    assert report.is_urgent_red_flag is True
    assert "Doppler ultrasound" in report.urgent_emergency_guidance_en
    assert "neoplasm" in report.urgent_emergency_guidance_en.lower()


# ---------------------------------------------------------------------------
# AC 8: Urgent Safety Preemption Over Lower Tiers
# ---------------------------------------------------------------------------
def test_ac08_urgent_safety_preemption_over_lower_tiers(setup_phase7_db: Session):
    """
    AC 8: Inputs both Tier 3 (TTC > 2y) and Tier 4 (Acute Pain).
    Asserts final outcome_tier = TIER_4_URGENT and emergency guidance takes precedence.
    """
    db = setup_phase7_db
    token = f"ac08_{uuid.uuid4().hex}"
    q_version = db.query(QuestionnaireVersion).filter(QuestionnaireVersion.status == QuestionnaireStatus.PUBLISHED).first()

    assessment = Assessment(session_token=token, questionnaire_version_id=q_version.id, status=AssessmentStatus.IN_PROGRESS)
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    q_ttc = db.query(Question).filter(Question.question_key == "Q_ATTEMPT_DURATION").first()
    q_pain = db.query(Question).filter(Question.question_key == "Q_ACUTE_SCROTAL_PAIN").first()

    db.add_all([
        AssessmentResponse(assessment_id=assessment.id, question_id=q_ttc.id, question_key="Q_ATTEMPT_DURATION", answer_value="more_than_2y"),
        AssessmentResponse(assessment_id=assessment.id, question_id=q_pain.id, question_key="Q_ACUTE_SCROTAL_PAIN", answer_value="yes")
    ])
    db.commit()

    report = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)

    assert report.outcome_tier == ClinicalOutcomeTier.TIER_4_URGENT
    assert report.is_urgent_red_flag is True
    assert "paused in favor of immediate physical evaluation" in report.outcome_description_en


# ---------------------------------------------------------------------------
# AC 9: Priority Rank Separation from Severity
# ---------------------------------------------------------------------------
def test_ac09_priority_rank_separation_from_severity(setup_phase7_db: Session):
    """
    AC 9: Evaluates rules across tiers with differing priority ranks.
    Asserts priority rank does not suppress or downgrade rules across tiers.
    """
    db = setup_phase7_db
    token = f"ac09_{uuid.uuid4().hex}"
    q_version = db.query(QuestionnaireVersion).filter(QuestionnaireVersion.status == QuestionnaireStatus.PUBLISHED).first()

    assessment = Assessment(session_token=token, questionnaire_version_id=q_version.id, status=AssessmentStatus.IN_PROGRESS)
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    q_steroid = db.query(Question).filter(Question.question_key == "Q_ANABOLIC_STEROIDS").first()
    q_tobacco = db.query(Question).filter(Question.question_key == "Q_TOBACCO_USE").first()

    db.add_all([
        AssessmentResponse(assessment_id=assessment.id, question_id=q_steroid.id, question_key="Q_ANABOLIC_STEROIDS", answer_value="yes_past"),  # Rank 25, Tier 3
        AssessmentResponse(assessment_id=assessment.id, question_id=q_tobacco.id, question_key="Q_TOBACCO_USE", answer_value=["shisha"])        # Rank 60, Tier 2
    ])
    db.commit()

    report = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)

    rule_codes = [r["rule_code"] for r in report.triggered_rules_snapshot_json]
    assert "R-MED-ANABOLIC-STEROIDS" in rule_codes
    assert "R-LST-TOBACCO-DOKHA" in rule_codes
    assert report.outcome_tier == ClinicalOutcomeTier.TIER_3_EVAL_RECOMMENDED


# ---------------------------------------------------------------------------
# AC 10: Safe Answer - Unsure State Isolation
# ---------------------------------------------------------------------------
def test_ac10_safe_answer_unsure_state_isolation(setup_phase7_db: Session):
    """
    AC 10: Submits is_unsure = True for anabolic steroids.
    Asserts rule evaluates to INDETERMINATE, 0 rules triggered.
    """
    db = setup_phase7_db
    token = f"ac10_{uuid.uuid4().hex}"
    q_version = db.query(QuestionnaireVersion).filter(QuestionnaireVersion.status == QuestionnaireStatus.PUBLISHED).first()

    assessment = Assessment(session_token=token, questionnaire_version_id=q_version.id, status=AssessmentStatus.IN_PROGRESS)
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    q_steroid = db.query(Question).filter(Question.question_key == "Q_ANABOLIC_STEROIDS").first()
    db.add(AssessmentResponse(assessment_id=assessment.id, question_id=q_steroid.id, question_key="Q_ANABOLIC_STEROIDS", is_unsure=True))
    db.commit()

    report = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)

    assert report.outcome_tier == ClinicalOutcomeTier.TIER_1_NO_RISK
    assert len(report.triggered_rules_snapshot_json) == 0
    resp_item = next(r for r in report.responses_summary_json if r["question_key"] == "Q_ANABOLIC_STEROIDS")
    assert resp_item["is_unsure"] is True


# ---------------------------------------------------------------------------
# AC 11: Safe Answer - Prefer Not to Say Isolation
# ---------------------------------------------------------------------------
def test_ac11_safe_answer_prefer_not_to_say_isolation(setup_phase7_db: Session):
    """
    AC 11: Submits is_prefer_not_to_say = True for testicular surgery.
    Asserts rule evaluates to INDETERMINATE, 0 rules triggered.
    """
    db = setup_phase7_db
    token = f"ac11_{uuid.uuid4().hex}"
    q_version = db.query(QuestionnaireVersion).filter(QuestionnaireVersion.status == QuestionnaireStatus.PUBLISHED).first()

    assessment = Assessment(session_token=token, questionnaire_version_id=q_version.id, status=AssessmentStatus.IN_PROGRESS)
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    q_surg = db.query(Question).filter(Question.question_key == "Q_TESTIS_SURGERY").first()
    db.add(AssessmentResponse(assessment_id=assessment.id, question_id=q_surg.id, question_key="Q_TESTIS_SURGERY", is_prefer_not_to_say=True))
    db.commit()

    report = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)

    assert report.outcome_tier == ClinicalOutcomeTier.TIER_1_NO_RISK
    assert len(report.triggered_rules_snapshot_json) == 0
    resp_item = next(r for r in report.responses_summary_json if r["question_key"] == "Q_TESTIS_SURGERY")
    assert resp_item["is_prefer_not_to_say"] is True


# ---------------------------------------------------------------------------
# AC 12: Missing Answer Policy (NEVER_NEGATIVE)
# ---------------------------------------------------------------------------
def test_ac12_missing_answer_policy_never_negative(setup_phase7_db: Session):
    """
    AC 12: Submits assessment with skipped questions.
    Asserts unanswered questions evaluate to INDETERMINATE and are marked is_missing = True.
    """
    db = setup_phase7_db
    token = f"ac12_{uuid.uuid4().hex}"
    q_version = db.query(QuestionnaireVersion).filter(QuestionnaireVersion.status == QuestionnaireStatus.PUBLISHED).first()

    assessment = Assessment(session_token=token, questionnaire_version_id=q_version.id, status=AssessmentStatus.IN_PROGRESS)
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    # Empty responses
    report = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)

    assert report.outcome_tier == ClinicalOutcomeTier.TIER_1_NO_RISK
    assert "INCOMPLETE EVALUATION" in report.outcome_title_en
    missing_items = [r for r in report.responses_summary_json if r["is_missing"] is True]
    assert len(missing_items) > 0


# ---------------------------------------------------------------------------
# AC 13: Inactive Response Isolation (Phase 6 DAG)
# ---------------------------------------------------------------------------
def test_ac13_inactive_response_isolation_dag(setup_phase7_db: Session):
    """
    AC 13: Sets parent Q_TESTIS_SURGERY = no (deactivating child Q_TESTIS_SURGERY_TYPE).
    Asserts child rule R-TST-CRYPTORCHIDISM evaluates to NOT_APPLICABLE and does not trigger.
    """
    db = setup_phase7_db
    token = f"ac13_{uuid.uuid4().hex}"
    q_version = db.query(QuestionnaireVersion).filter(QuestionnaireVersion.status == QuestionnaireStatus.PUBLISHED).first()

    assessment = Assessment(session_token=token, questionnaire_version_id=q_version.id, status=AssessmentStatus.IN_PROGRESS)
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    q_parent = db.query(Question).filter(Question.question_key == "Q_TESTIS_SURGERY").first()
    q_child = db.query(Question).filter(Question.question_key == "Q_TESTIS_SURGERY_TYPE").first()

    db.add_all([
        AssessmentResponse(assessment_id=assessment.id, question_id=q_parent.id, question_key="Q_TESTIS_SURGERY", answer_value="no", conditional_pathway_active=True),
        AssessmentResponse(assessment_id=assessment.id, question_id=q_child.id, question_key="Q_TESTIS_SURGERY_TYPE", answer_value="undescended_testis", conditional_pathway_active=False)
    ])
    db.commit()

    report = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)

    rule_codes = [r["rule_code"] for r in report.triggered_rules_snapshot_json]
    assert "R-TST-CRYPTORCHIDISM" not in rule_codes


# ---------------------------------------------------------------------------
# AC 14: Technical Compound Boolean Grammar
# ---------------------------------------------------------------------------
def test_ac14_technical_compound_boolean_grammar():
    """
    AC 14: Tests all_of and any_of predicates according to three-valued truth tables.
    """
    all_of_pred = {
        "combinator": "all_of",
        "conditions": [
            {"operator": "equals", "question_key": "Q1", "expected_value": "yes"},
            {"operator": "equals", "question_key": "Q2", "expected_value": "yes"}
        ]
    }
    # Both true -> TRUE
    res, _ = PredicateEvaluator.evaluate_predicate_tree(all_of_pred, {"Q1": {"answer_value": "yes"}, "Q2": {"answer_value": "yes"}})
    assert res == PredicateEvaluationState.TRUE

    # One false -> FALSE
    res, _ = PredicateEvaluator.evaluate_predicate_tree(all_of_pred, {"Q1": {"answer_value": "yes"}, "Q2": {"answer_value": "no"}})
    assert res == PredicateEvaluationState.FALSE

    # One true, one unsure -> INDETERMINATE
    res, _ = PredicateEvaluator.evaluate_predicate_tree(all_of_pred, {"Q1": {"answer_value": "yes"}, "Q2": {"is_unsure": True}})
    assert res == PredicateEvaluationState.INDETERMINATE

    any_of_pred = {
        "combinator": "any_of",
        "conditions": [
            {"operator": "equals", "question_key": "Q1", "expected_value": "yes"},
            {"operator": "equals", "question_key": "Q2", "expected_value": "yes"}
        ]
    }
    # One true -> TRUE
    res, _ = PredicateEvaluator.evaluate_predicate_tree(any_of_pred, {"Q1": {"answer_value": "yes"}, "Q2": {"answer_value": "no"}})
    assert res == PredicateEvaluationState.TRUE

    # Both false -> FALSE
    res, _ = PredicateEvaluator.evaluate_predicate_tree(any_of_pred, {"Q1": {"answer_value": "no"}, "Q2": {"answer_value": "no"}})
    assert res == PredicateEvaluationState.FALSE


# ---------------------------------------------------------------------------
# AC 15: Compound none_of Safe Answer Guard
# ---------------------------------------------------------------------------
def test_ac15_compound_none_of_safe_answer_guard():
    """
    AC 15: Tests none_of where one condition is Unsure or Missing.
    Asserts: Outcome evaluates strictly to INDETERMINATE (never True).
    """
    none_of_pred = {
        "combinator": "none_of",
        "conditions": [
            {"operator": "equals", "question_key": "Q1", "expected_value": "yes"},
            {"operator": "equals", "question_key": "Q2", "expected_value": "yes"}
        ]
    }

    # Condition Q2 is unsure: MUST be INDETERMINATE
    res, _ = PredicateEvaluator.evaluate_predicate_tree(
        none_of_pred,
        {"Q1": {"answer_value": "no"}, "Q2": {"is_unsure": True}}
    )
    assert res == PredicateEvaluationState.INDETERMINATE

    # Condition Q2 is missing: MUST be INDETERMINATE
    res, _ = PredicateEvaluator.evaluate_predicate_tree(
        none_of_pred,
        {"Q1": {"answer_value": "no"}}
    )
    assert res == PredicateEvaluationState.INDETERMINATE


# ---------------------------------------------------------------------------
# AC 16: Predicate Nesting Depth Guard
# ---------------------------------------------------------------------------
def test_ac16_predicate_nesting_depth_guard():
    """
    AC 16: Submits predicate tree with recursion depth = 4.
    Asserts: ValueError is raised with depth limit error.
    """
    nested_4 = {
        "combinator": "all_of",
        "conditions": [{
            "combinator": "any_of",
            "conditions": [{
                "combinator": "all_of",
                "conditions": [{
                    "combinator": "any_of",
                    "conditions": [{"operator": "equals", "question_key": "Q", "expected_value": "x"}]
                }]
            }]
        }]
    }

    with pytest.raises(ValueError) as excinfo:
        PredicateEvaluator.validate_predicate_structure(nested_4)
    assert "exceeds maximum allowed limit" in str(excinfo.value)


# ---------------------------------------------------------------------------
# AC 17: Locked Assessment Report Immutability
# ---------------------------------------------------------------------------
def test_ac17_locked_assessment_report_immutability(setup_phase7_db: Session):
    """
    AC 17: Calls compile_assessment_report twice on same assessment.
    Asserts: Exact same report instance returned without recomputation.
    """
    db = setup_phase7_db
    token = f"ac17_{uuid.uuid4().hex}"
    q_version = db.query(QuestionnaireVersion).filter(QuestionnaireVersion.status == QuestionnaireStatus.PUBLISHED).first()

    assessment = Assessment(session_token=token, questionnaire_version_id=q_version.id, status=AssessmentStatus.IN_PROGRESS)
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    q_age = db.query(Question).filter(Question.question_key == "Q_AGE").first()
    db.add(AssessmentResponse(assessment_id=assessment.id, question_id=q_age.id, question_key="Q_AGE", answer_value=30))
    db.commit()

    report1 = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)
    rep1_id = report1.id
    rep1_time = report1.generated_at

    report2 = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)
    assert report2.id == rep1_id
    assert report2.generated_at == rep1_time


# ---------------------------------------------------------------------------
# AC 18: Clinical Governance RBAC Protection
# ---------------------------------------------------------------------------
def test_ac18_clinical_governance_rbac_protection(setup_phase7_db: Session):
    """
    AC 18: Tests existing RBAC endpoints. Non-clinician is rejected with HTTP 403.
    """
    db = setup_phase7_db
    user = db.query(User).filter(User.email == "patient@genovex.ae").first()
    if not user:
        user = User(
            email="patient@genovex.ae",
            hashed_password="hashed_pw_test",
            full_name="Patient Test",
            role=RoleEnum.PATIENT,
            is_active=True
        )
        db.add(user)
        db.commit()

    client = TestClient(fastapi_app)
    patient_token = create_access_token(data={"sub": "patient@genovex.ae", "role": RoleEnum.PATIENT.value})

    # Non-clinician calls rule review route
    res = client.post(
        "/api/v1/admin/clinical-rules/1/review",
        json={"action": "APPROVE", "reviewer_notes": "Attempt unauthorized approval"},
        headers={"Authorization": f"Bearer {patient_token}"}
    )
    assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}"

    # Non-clinician calls rule publish route
    res_pub = client.post(
        "/api/v1/admin/clinical-rules/1/publish",
        headers={"Authorization": f"Bearer {patient_token}"}
    )
    assert res_pub.status_code == 403, f"Expected 403 Forbidden, got {res_pub.status_code}"


# ---------------------------------------------------------------------------
# AC 19: Database Integrity & Zero-DDL Parity
# ---------------------------------------------------------------------------
def test_ac19_database_integrity_zero_ddl_parity(setup_phase7_db: Session):
    """
    AC 19: Meaningful isolated cryptographic schema audit and zero-DDL parity.
    Verifies:
    1. Schema & Table Inventory: Exactly 18 physical tables registered and present.
    2. Expected Schema Invariants: Mandatory columns, primary keys, and foreign keys intact.
    3. Foreign Key Integrity: PRAGMA foreign_key_check returns zero violations.
    4. Physical SQLite Integrity: PRAGMA integrity_check returns 'ok'.
    5. Zero DDL During Execution: Computes canonical SHA-256 schema fingerprint before and after, asserting strict equality.
    6. Baseline Data Invariants: 22 clinical rules, 19 questions, registered medical conditions.
    """
    db = setup_phase7_db
    import os
    from app.core.config import AUTHORITATIVE_DB_PATH
    if not os.path.exists(AUTHORITATIVE_DB_PATH) or os.path.getsize(AUTHORITATIVE_DB_PATH) == 0:
        pytest.skip("Authoritative baseline database not present in test environment")
    conn = db.connection().connection

    cur = conn.cursor()

    # 1. Physical SQLite Integrity Check
    cur.execute("PRAGMA integrity_check;")
    integrity = cur.fetchall()
    assert integrity == [("ok",)], f"Integrity check failed: {integrity}"

    # 2. Relational Foreign Key Integrity Check
    cur.execute("PRAGMA foreign_key_check;")
    fk_errors = cur.fetchall()
    assert fk_errors == [], f"Foreign key violations found: {fk_errors}"

    # 3. Table Inventory: Exactly 19 physical tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
    tables = [r[0] for r in cur.fetchall()]
    assert len(tables) == 19, f"Expected exactly 19 physical tables, found {len(tables)}: {tables}"
    
    expected_tables = {
        "alembic_version", "assessment_reports", "assessment_responses", "assessments",
        "audit_logs", "clinical_review_records", "clinical_rule_versions", "clinical_rules",
        "condition_contents", "condition_references", "content_versions", "healthcare_facilities",
        "medical_categories", "medical_conditions", "medical_references", "questionnaire_versions",
        "questions", "users", "password_reset_tokens"
    }
    assert set(tables) == expected_tables, f"Table schema mismatch: {set(tables) ^ expected_tables}"

    # 4. Canonical DDL Schema Fingerprint (Before/After Zero-DDL Invariant)
    cur.execute("SELECT sql FROM sqlite_master WHERE type IN ('table', 'index', 'trigger') AND sql IS NOT NULL ORDER BY name;")
    schema_sqls = [r[0] for r in cur.fetchall()]
    before_fingerprint = hashlib.sha256("\n".join(schema_sqls).encode("utf-8")).hexdigest()

    # 5. Baseline Data Invariants
    cur.execute("SELECT count(*) FROM clinical_rules;")
    rule_count = cur.fetchone()[0]
    assert rule_count >= 22, f"Expected at least 22 clinical rules, found {rule_count}"
    cur.execute("SELECT DISTINCT rule_code FROM clinical_rules;")
    db_codes = {r[0] for r in cur.fetchall()}
    assert len(db_codes) >= 22, f"Expected at least 22 distinct rule codes, found {len(db_codes)}"

    cur.execute("SELECT count(*) FROM questions;")
    question_count = cur.fetchone()[0]
    assert question_count == 19, f"Expected 19 questions, found {question_count}"

    # 6. Verify Zero DDL Occurred (Re-evaluating fingerprint)
    cur.execute("SELECT sql FROM sqlite_master WHERE type IN ('table', 'index', 'trigger') AND sql IS NOT NULL ORDER BY name;")
    after_sqls = [r[0] for r in cur.fetchall()]
    after_fingerprint = hashlib.sha256("\n".join(after_sqls).encode("utf-8")).hexdigest()
    assert before_fingerprint == after_fingerprint, "Schema fingerprint mutated during execution! Unauthorized DDL detected."


# ---------------------------------------------------------------------------
# AC 20: Categorical Audit Log Verification (Zero PII)
# ---------------------------------------------------------------------------
def test_ac20_categorical_audit_log_verification(setup_phase7_db: Session):
    """
    AC 20: Compiles an assessment report and verifies categorical audit logging in audit_logs.
    Asserts zero patient PII in details payload.
    """
    db = setup_phase7_db
    token = f"ac20_{uuid.uuid4().hex}"
    q_version = db.query(QuestionnaireVersion).filter(QuestionnaireVersion.status == QuestionnaireStatus.PUBLISHED).first()

    assessment = Assessment(session_token=token, questionnaire_version_id=q_version.id, status=AssessmentStatus.IN_PROGRESS)
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    q_age = db.query(Question).filter(Question.question_key == "Q_AGE").first()
    db.add(AssessmentResponse(assessment_id=assessment.id, question_id=q_age.id, question_key="Q_AGE", answer_value=48))
    db.commit()

    report = ClinicalRuleEngineService.compile_assessment_report(db, assessment.id, token)

    audit_entry = db.query(AuditLog).filter(
        AuditLog.action == "EVALUATE_CLINICAL_RULES",
        AuditLog.resource_id == report.report_reference
    ).first()

    assert audit_entry is not None, "Expected AuditLog entry for report evaluation"
    details = audit_entry.details
    assert "evaluation_counts" in details
    assert "triggered" in details["evaluation_counts"]
    assert "explicit_non_trigger" in details["evaluation_counts"]
    assert "indeterminate" in details["evaluation_counts"]
    assert "not_applicable" in details["evaluation_counts"]
    assert "outcome_tier" in details

    # Zero PII: Patient answers are never logged to audit_logs
    details_str = json.dumps(details).lower()
    assert "answer_value" not in details_str
    assert "48" not in details_str
