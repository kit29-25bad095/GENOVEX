import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.questionnaire import (
    QuestionnaireVersion, QuestionnaireStatus, QuestionDomain, QuestionType,
    Question, Assessment, AssessmentStatus, AssessmentResponse
)
from app.schemas.questionnaire import (
    SaveDomainResponsesRequest, AnswerInput
)
from app.services.questionnaire_service import QuestionnaireService, DOMAINS_METADATA

@pytest.fixture
def db_session():
    """Create an isolated in-memory SQLite database for testing questionnaire logic."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed test questionnaire version
    version = QuestionnaireVersion(
        id=1,
        version_tag="v1.0.0-test",
        title_en="Test Questionnaire",
        title_ar="استبيان تجريبي",
        status=QuestionnaireStatus.PUBLISHED
    )
    session.add(version)

    # Seed questions: parent question, conditional child question, urgent red flag question
    q_parent = Question(
        id=101,
        version_id=1,
        domain_code=QuestionDomain.LIFESTYLE_HABITS,
        question_key="smoke_habit",
        text_en="Do you smoke?",
        text_ar="هل تدخن؟",
        question_type=QuestionType.YES_NO,
        clinical_rationale_en="Smoking impacts semen quality",
        clinical_rationale_ar="التدخين يؤثر على جودة السائل المنوي",
        display_order=1
    )
    q_child = Question(
        id=102,
        version_id=1,
        domain_code=QuestionDomain.LIFESTYLE_HABITS,
        question_key="smoke_frequency",
        text_en="How many cigarettes per day?",
        text_ar="كم عدد السجائر يوميا؟",
        question_type=QuestionType.SINGLE_CHOICE,
        conditional_parent_key="smoke_habit",
        conditional_trigger_values=[True, "yes", "true"],
        clinical_rationale_en="Dose-response relationship",
        clinical_rationale_ar="علاقة طردية",
        display_order=2
    )
    q_red_flag = Question(
        id=103,
        version_id=1,
        domain_code=QuestionDomain.TESTICULAR_HISTORY,
        question_key="testicular_swelling",
        text_en="Do you have severe pain or sudden swelling?",
        text_ar="هل تشعر بألم شديد أو تورم مفاجئ؟",
        question_type=QuestionType.YES_NO,
        is_urgent_red_flag=True,
        clinical_rationale_en="Potential testicular torsion or acute pathology",
        clinical_rationale_ar="احتمال التواء الخصية أو اعتلال حاد",
        display_order=1
    )
    session.add_all([q_parent, q_child, q_red_flag])
    session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()

def test_save_responses_canonical_answers_format(db_session):
    """Test saving responses using canonical AnswerInput array."""
    assessment = Assessment(
        id=str(uuid.uuid4()),
        session_token="sess-canonical-01",
        questionnaire_version_id=1,
        status=AssessmentStatus.IN_PROGRESS
    )
    db_session.add(assessment)
    db_session.commit()

    req = SaveDomainResponsesRequest(
        domain_code=QuestionDomain.LIFESTYLE_HABITS,
        answers=[
            AnswerInput(
                question_id=101,
                question_key="smoke_habit",
                answer_value=True
            )
        ]
    )

    resp = QuestionnaireService.save_domain_responses(db_session, assessment.id, req)
    assert resp.saved_count == 1

    saved = db_session.query(AssessmentResponse).filter(
        AssessmentResponse.assessment_id == assessment.id,
        AssessmentResponse.question_key == "smoke_habit"
    ).first()
    assert saved is not None
    assert saved.answer_value is True
    assert saved.is_unsure is False
    assert saved.is_prefer_not_to_say is False

def test_save_responses_dictionary_format_with_unsure_and_prefer_not_to_say(db_session):
    """
    Test dual contract: frontend dictionary format with 'not_sure' and 'prefer_not_to_say'.
    Verifies that 'not_sure' sets is_unsure=True and is not converted to False/negative answer.
    """
    assessment = Assessment(
        id=str(uuid.uuid4()),
        session_token="sess-dict-02",
        questionnaire_version_id=1,
        status=AssessmentStatus.IN_PROGRESS
    )
    db_session.add(assessment)
    db_session.commit()

    req = SaveDomainResponsesRequest(
        domain_code=QuestionDomain.LIFESTYLE_HABITS,
        responses={
            "smoke_habit": "not_sure"
        }
    )

    resp = QuestionnaireService.save_domain_responses(db_session, assessment.id, req)
    assert resp.saved_count == 1

    saved = db_session.query(AssessmentResponse).filter(
        AssessmentResponse.assessment_id == assessment.id,
        AssessmentResponse.question_key == "smoke_habit"
    ).first()
    assert saved is not None
    assert saved.is_unsure is True
    assert saved.is_prefer_not_to_say is False
    assert saved.answer_value is None  # Not boolean False

    # Test prefer_not_to_say
    req2 = SaveDomainResponsesRequest(
        domain_code=QuestionDomain.LIFESTYLE_HABITS,
        responses={
            "smoke_habit": "prefer_not_to_say"
        }
    )
    QuestionnaireService.save_domain_responses(db_session, assessment.id, req2)
    db_session.refresh(saved)
    assert saved.is_prefer_not_to_say is True
    assert saved.is_unsure is False
    assert saved.answer_value is None

def test_dynamic_conditional_question_visibility(db_session):
    """Test that conditional follow-up questions only appear when parent condition is met."""
    assessment = Assessment(
        id=str(uuid.uuid4()),
        session_token="sess-vis-03",
        questionnaire_version_id=1,
        status=AssessmentStatus.IN_PROGRESS
    )
    db_session.add(assessment)
    db_session.commit()

    # 1. Without parent answer: child question smoke_frequency must NOT be visible
    lifestyle_idx = next(i for i, d in enumerate(DOMAINS_METADATA) if d["code"] == QuestionDomain.LIFESTYLE_HABITS)
    
    dq_resp = QuestionnaireService.get_domain_questions(db_session, assessment.id, lifestyle_idx)
    visible_keys = [q.question_key for q in dq_resp.questions]
    assert "smoke_habit" in visible_keys
    assert "smoke_frequency" not in visible_keys

    # 2. Answer parent with True (trigger value)
    req = SaveDomainResponsesRequest(
        domain_code=QuestionDomain.LIFESTYLE_HABITS,
        answers=[AnswerInput(question_id=101, question_key="smoke_habit", answer_value=True)]
    )
    QuestionnaireService.save_domain_responses(db_session, assessment.id, req)

    # Now child question must be visible
    dq_resp2 = QuestionnaireService.get_domain_questions(db_session, assessment.id, lifestyle_idx)
    visible_keys2 = [q.question_key for q in dq_resp2.questions]
    assert "smoke_habit" in visible_keys2
    assert "smoke_frequency" in visible_keys2

def test_urgent_red_flag_detection(db_session):
    """Affirmative answer to urgent red-flag question triggers urgent alert."""
    assessment = Assessment(
        id=str(uuid.uuid4()),
        session_token="sess-redflag-04",
        questionnaire_version_id=1,
        status=AssessmentStatus.IN_PROGRESS
    )
    db_session.add(assessment)
    db_session.commit()

    req = SaveDomainResponsesRequest(
        domain_code=QuestionDomain.TESTICULAR_HISTORY,
        answers=[
            AnswerInput(question_id=103, question_key="testicular_swelling", answer_value=True)
        ]
    )
    resp = QuestionnaireService.save_domain_responses(db_session, assessment.id, req)
    assert "testicular_swelling" in resp.urgent_red_flags_detected
