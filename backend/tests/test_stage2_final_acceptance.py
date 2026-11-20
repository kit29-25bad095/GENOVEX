import os
import tempfile
import uuid
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import IntegrityError

from main import app as fastapi_app
from app.core.database import engine as app_engine, set_sqlite_pragma, Base
from app.models.questionnaire import (
    QuestionnaireVersion, QuestionnaireStatus, QuestionDomain, QuestionType,
    Question, Assessment, AssessmentStatus, AssessmentResponse
)
from app.models.clinical_rules import (
    ClinicalRule, ClinicalOutcomeTier, ClinicalRuleStatus
)
from app.models.assessment_report import AssessmentReport
from app.schemas.questionnaire import SaveDomainResponsesRequest, AnswerInput
from app.schemas.assessment_report import AssessmentReportResponse
from app.services.questionnaire_service import QuestionnaireService
from app.services.clinical_rule_engine import ClinicalRuleEngineService

# ---------------------------------------------------------------------------
# Requirement 1 & 4: API Endpoint Integration Tests (Frontend Exact Payloads)
# ---------------------------------------------------------------------------

def test_questionnaire_frontend_exact_request_contract():
    """
    1. Complete questionnaire request contract:
       - Uses exact payload structure sent by frontend: {"domain_index": 0, "responses": {...}}
       - Calls actual FastAPI endpoint POST /api/v1/questionnaire/assessments/{assessment_id}/save-domain
       - Verifies domain selection, persistence, and retrieval via GET .../domain/0
    """
    client = TestClient(fastapi_app)

    # 1. Initialize assessment
    start_res = client.post("/api/v1/questionnaire/assessments/start", json={})
    assert start_res.status_code == 200, start_res.text
    start_data = start_res.json()
    assessment_id = start_data["assessment_id"]
    csrf_token = start_data.get("csrf_token")
    assert assessment_id is not None

    # 2. Get questions for domain 0
    d0_res = client.get(f"/api/v1/questionnaire/assessments/{assessment_id}/domain/0")
    assert d0_res.status_code == 200, d0_res.text
    d0_data = d0_res.json()
    assert d0_data["domain_index"] == 0
    assert len(d0_data["questions"]) > 0

    first_q_key = d0_data["questions"][0]["question_code"]

    # 3. Save domain using frontend's EXACT payload: { domain_index, responses }
    frontend_payload = {
        "domain_index": 0,
        "responses": {
            first_q_key: "not_sure"
        }
    }
    save_res = client.post(
        f"/api/v1/questionnaire/assessments/{assessment_id}/save-domain",
        json=frontend_payload,
        headers={"X-CSRF-Token": csrf_token} if csrf_token else {}
    )
    assert save_res.status_code == 200, save_res.text
    save_data = save_res.json()
    assert save_data["saved_count"] >= 1

    # 4. Verify retrieval via GET domain 0
    d0_verify = client.get(f"/api/v1/questionnaire/assessments/{assessment_id}/domain/0")
    assert d0_verify.status_code == 200
    saved_answers = d0_verify.json()["saved_responses"]
    assert first_q_key in saved_answers
    assert saved_answers[first_q_key]["is_unsure"] is True
    assert saved_answers[first_q_key]["answer_value"] is None

def test_report_wire_contract_api_response():
    """
    4. Report wire contract:
       - Evaluates an assessment through the actual FastAPI endpoint POST /api/v1/assessment/{session_token}/evaluate
       - Verifies that wire JSON keys match all frontend-consumed field names:
         overall_tier, has_urgent_flags, urgent_guidance, identified_risk_factors,
         evidence_citations, non_diagnostic_summary_en, non_diagnostic_summary_ar,
         created_at, and assessment_id as a UUID string.
    """
    client = TestClient(fastapi_app)

    # 1. Start assessment
    start_res = client.post("/api/v1/questionnaire/assessments/start", json={})
    assert start_res.status_code == 200
    start_data = start_res.json()
    session_token = start_data["session_token"]
    assessment_id = start_data["assessment_id"]

    # Mark assessment as submitted per Phase 8 submission lock policy
    from app.models.questionnaire import Assessment, AssessmentStatus
    from app.core.database import SessionLocal
    with SessionLocal() as db:
        a = db.query(Assessment).filter(Assessment.session_token == session_token).first()
        if a:
            a.status = AssessmentStatus.SUBMITTED
            db.commit()

    # 2. Evaluate assessment via actual API endpoint
    eval_res = client.post(f"/api/v1/assessment/{session_token}/evaluate")
    # Supports both released 200 payload and 422 clinical governance withholding gate
    assert eval_res.status_code in (200, 422), eval_res.text
    if eval_res.status_code == 200:
        report_json = eval_res.json()
        # 3. Assert wire contract properties
        assert isinstance(report_json["assessment_id"], str)
        assert report_json["assessment_id"] == assessment_id
        assert "overall_tier" in report_json
        assert report_json["overall_tier"] in [
            "ROUTINE_PREVENTIVE_CARE",
            "LIFESTYLE_MODIFIABLE_FACTORS",
            "SPECIALIST_EVALUATION_RECOMMENDED",
            "URGENT_MEDICAL_ASSESSMENT"
        ]
        assert "has_urgent_flags" in report_json
        assert isinstance(report_json["has_urgent_flags"], bool)
        assert "urgent_guidance" in report_json
        assert "identified_risk_factors" in report_json
        assert isinstance(report_json["identified_risk_factors"], list)
        assert "evidence_citations" in report_json
        assert isinstance(report_json["evidence_citations"], list)
        assert "non_diagnostic_summary_en" in report_json
        assert "non_diagnostic_summary_ar" in report_json
        assert "created_at" in report_json

        # Ensure internal DB suffix fields are not leaked as canonical keys
        assert "identified_risk_factors_json" not in report_json
        assert "triggered_rules_snapshot_json" not in report_json
        assert "responses_summary_json" not in report_json
        assert "evidence_citations_json" not in report_json
    else:
        err_json = eval_res.json()
        detail = err_json.get("detail", {})
        assert detail.get("code") in ("INCOMPLETE_EVALUATION_WITHHELD", "CLINICAL_RULES_PENDING_APPROVAL")

# ---------------------------------------------------------------------------
# Requirement 2: Actual Application Database Engine Verification
# ---------------------------------------------------------------------------

def test_actual_application_engine_concurrent_foreign_keys_and_rejection():
    """
    2. Actual application database engine:
       - Verifies connection listener on app_engine.
       - Holds two simultaneous connections and verifies PRAGMA foreign_keys=1 on both.
       - Disposes engine pool and verifies fresh connection still has foreign_keys=1.
       - Tests invalid foreign key rejection on disposable database without touching live DB.
    """
    # 1. Verify listener on actual application engine
    with app_engine.connect() as conn1:
        with app_engine.connect() as conn2:
            dbapi1 = conn1.connection.dbapi_connection
            dbapi2 = conn2.connection.dbapi_connection
            assert dbapi1 is not dbapi2, "Expected distinct DBAPI connections"

            fk1 = conn1.execute(text("PRAGMA foreign_keys;")).scalar()
            fk2 = conn2.execute(text("PRAGMA foreign_keys;")).scalar()
            assert fk1 == 1, f"Expected foreign_keys=1 on conn1, got {fk1}"
            assert fk2 == 1, f"Expected foreign_keys=1 on conn2, got {fk2}"

    # 2. Pool disposal and reconnect
    app_engine.dispose()
    with app_engine.connect() as conn3:
        fk3 = conn3.execute(text("PRAGMA foreign_keys;")).scalar()
        assert fk3 == 1, f"Expected foreign_keys=1 on conn3 after dispose, got {fk3}"

    # 3. Disposable test database foreign key rejection test
    temp_dir = tempfile.mkdtemp()
    temp_db_path = os.path.join(temp_dir, "test_disposable_fk.db")
    temp_engine = create_engine(f"sqlite:///{temp_db_path}")
    event.listen(temp_engine, "connect", set_sqlite_pragma)

    TestBase = declarative_base()
    class Parent(TestBase):
        __tablename__ = "parents"
        id = Column(Integer, primary_key=True)
        name = Column(String(50))

    class Child(TestBase):
        __tablename__ = "children"
        id = Column(Integer, primary_key=True)
        parent_id = Column(Integer, ForeignKey("parents.id", ondelete="CASCADE"), nullable=False)

    TestBase.metadata.create_all(temp_engine)
    Session = sessionmaker(bind=temp_engine)
    session = Session()

    try:
        # Invalid FK insert must raise IntegrityError
        invalid_child = Child(id=1, parent_id=8888)
        session.add(invalid_child)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
    finally:
        session.close()
        temp_engine.dispose()
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)
        os.rmdir(temp_dir)

# ---------------------------------------------------------------------------
# Requirement 3: Tri-State Persistence & Safe Clinical Evaluation
# ---------------------------------------------------------------------------

def test_tri_state_persistence_and_clinical_rule_evaluation():
    """
    3. Tri-state persistence:
       - Tests affirmative (True), negative (False), unsure ("not_sure"),
         prefer-not-to-say ("prefer_not_to_say"), and unanswered (missing).
       - Confirms their distinction survives persistence and retrieval.
       - Confirms unanswered is not converted to negative response.
       - Confirms clinical evaluation does not treat unknown or declined as negative evidence.
    """
    temp_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(temp_engine)
    Session = sessionmaker(bind=temp_engine)
    session = Session()

    try:
        # Seed test version & questions
        version = QuestionnaireVersion(
            id=1,
            version_tag="v1.0.0-tristate",
            title_en="Tri-State Test",
            title_ar="اختبار ثلاثي الحالة",
            status=QuestionnaireStatus.PUBLISHED
        )
        session.add(version)

        # Questions for 5 states:
        q_yes = Question(
            id=201, version_id=1, domain_code=QuestionDomain.LIFESTYLE_HABITS,
            question_key="Q_AFFIRMATIVE", text_en="Affirmative?", text_ar="نعم؟",
            question_type=QuestionType.YES_NO, clinical_rationale_en="test", clinical_rationale_ar="test"
        )
        q_no = Question(
            id=202, version_id=1, domain_code=QuestionDomain.LIFESTYLE_HABITS,
            question_key="Q_NEGATIVE", text_en="Negative?", text_ar="لا؟",
            question_type=QuestionType.YES_NO, clinical_rationale_en="test", clinical_rationale_ar="test"
        )
        q_unsure = Question(
            id=203, version_id=1, domain_code=QuestionDomain.LIFESTYLE_HABITS,
            question_key="Q_UNSURE", text_en="Unsure?", text_ar="غير متأكد؟",
            question_type=QuestionType.YES_NO, clinical_rationale_en="test", clinical_rationale_ar="test"
        )
        q_decline = Question(
            id=204, version_id=1, domain_code=QuestionDomain.LIFESTYLE_HABITS,
            question_key="Q_DECLINE", text_en="Prefer not to say?", text_ar="أفضل عدم الإجابة؟",
            question_type=QuestionType.YES_NO, clinical_rationale_en="test", clinical_rationale_ar="test"
        )
        q_missing = Question(
            id=205, version_id=1, domain_code=QuestionDomain.LIFESTYLE_HABITS,
            question_key="Q_UNANSWERED", text_en="Unanswered?", text_ar="غير مجاب؟",
            question_type=QuestionType.YES_NO, clinical_rationale_en="test", clinical_rationale_ar="test"
        )
        session.add_all([q_yes, q_no, q_unsure, q_decline, q_missing])

        # Add clinical rule that triggers ONLY if affirmative
        rule = ClinicalRule(
            id=1, rule_code="R-TEST-AFFIRMATIVE", rule_version="1.0.0",
            domain_code=QuestionDomain.LIFESTYLE_HABITS,
            title_en="Affirmative Trigger", title_ar="تفعيل إيجابي",
            outcome_tier=ClinicalOutcomeTier.TIER_2_RISK_FACTORS,
            trigger_criteria={"question_key": "Q_AFFIRMATIVE", "operator": "equals", "expected_value": True},
            clinical_rationale_en="Test rationale", clinical_rationale_ar="Test rationale",
            status=ClinicalRuleStatus.PUBLISHED
        )
        session.add(rule)

        assessment = Assessment(
            id=str(uuid.uuid4()),
            session_token="token-tristate-123",
            questionnaire_version_id=1,
            status=AssessmentStatus.IN_PROGRESS
        )
        session.add(assessment)
        session.commit()

        # Save responses for 4 questions (leaving Q_UNANSWERED missing)
        req = SaveDomainResponsesRequest(
            domain_code=QuestionDomain.LIFESTYLE_HABITS,
            responses={
                "Q_AFFIRMATIVE": True,
                "Q_NEGATIVE": False,
                "Q_UNSURE": "not_sure",
                "Q_DECLINE": "prefer_not_to_say"
            }
        )
        QuestionnaireService.save_domain_responses(session, assessment.id, req)

        # 1. Verify DB persistence distinctions
        responses = {r.question_key: r for r in session.query(AssessmentResponse).filter(AssessmentResponse.assessment_id == assessment.id).all()}
        assert len(responses) == 4
        assert "Q_UNANSWERED" not in responses  # Completely absent from responses table

        # State 1: Affirmative
        r_yes = responses["Q_AFFIRMATIVE"]
        assert r_yes.answer_value is True
        assert r_yes.is_unsure is False
        assert r_yes.is_prefer_not_to_say is False

        # State 2: Negative
        r_no = responses["Q_NEGATIVE"]
        assert r_no.answer_value is False
        assert r_no.is_unsure is False
        assert r_no.is_prefer_not_to_say is False

        # State 3: Unsure
        r_unsure = responses["Q_UNSURE"]
        assert r_unsure.answer_value is None
        assert r_unsure.is_unsure is True
        assert r_unsure.is_prefer_not_to_say is False

        # State 4: Prefer Not to Say
        r_decline = responses["Q_DECLINE"]
        assert r_decline.answer_value is None
        assert r_decline.is_unsure is False
        assert r_decline.is_prefer_not_to_say is True

        # 2. Verify Clinical Evaluation behavior
        # Evaluate assessment
        report = ClinicalRuleEngineService.compile_assessment_report(
            db=session,
            assessment_id=assessment.id,
            session_token=assessment.session_token
        )

        # Responses summary breakdown
        summary_by_key = {item["question_key"]: item for item in report.responses_summary_json}

        # Check Q_UNANSWERED in summary
        assert "Q_UNANSWERED" in summary_by_key
        assert summary_by_key["Q_UNANSWERED"]["is_missing"] is True
        assert summary_by_key["Q_UNANSWERED"]["is_unsure"] is False
        assert summary_by_key["Q_UNANSWERED"]["is_prefer_not_to_say"] is False
        assert "Not answered" in summary_by_key["Q_UNANSWERED"]["answer_display_en"]

        # Check Q_UNSURE in summary
        assert summary_by_key["Q_UNSURE"]["is_unsure"] is True
        assert summary_by_key["Q_UNSURE"]["is_missing"] is False

        # Check Q_DECLINE in summary
        assert summary_by_key["Q_DECLINE"]["is_prefer_not_to_say"] is True
        assert summary_by_key["Q_DECLINE"]["is_missing"] is False

        # Check that ONLY Q_AFFIRMATIVE triggered rule
        triggered_codes = [tr["rule_code"] for tr in report.triggered_rules_snapshot_json]
        assert triggered_codes == ["R-TEST-AFFIRMATIVE"]

    finally:
        session.close()
        Base.metadata.drop_all(temp_engine)
        temp_engine.dispose()
