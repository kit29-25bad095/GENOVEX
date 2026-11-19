import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone
from fastapi import HTTPException

from app.core.database import Base
from app.core.security import User, RoleEnum, get_password_hash
from app.models.questionnaire import (
    QuestionnaireVersion, Question, Assessment, AssessmentResponse,
    QuestionnaireStatus, QuestionDomain, QuestionType, AssessmentStatus
)
from app.schemas.questionnaire import (
    QuestionnaireVersionCreate, QuestionCreate, QuestionOptionSchema,
    SaveDomainResponsesRequest, AnswerInput
)
from app.services.questionnaire_service import QuestionnaireService
from app.core.seed_questionnaire import seed_questionnaire_v1

# In-memory SQLite for high-speed, isolated unit and integration testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()

    # Seed Users
    admin_user = User(
        email="admin@test.health",
        hashed_password=get_password_hash("AdminPass123"),
        full_name="Sarah Jenkins",
        role=RoleEnum.ADMIN,
        credentials_summary="Clinical Content Operations"
    )
    clinician_user = User(
        email="clinician@test.health",
        hashed_password=get_password_hash("ClinicianPass123"),
        full_name="Dr. Tarek Al-Mansoor",
        role=RoleEnum.CLINICIAN,
        credentials_summary="Consultant Andrologist / DHA Licensed"
    )
    patient_user = User(
        email="patient@test.health",
        hashed_password=get_password_hash("PatientPass123"),
        full_name="Rashid Al-Nuaimi",
        role=RoleEnum.PATIENT,
        credentials_summary="Registered Patient"
    )
    session.add_all([admin_user, clinician_user, patient_user])
    session.commit()

    # Seed initial questionnaire v1.0.0
    seed_questionnaire_v1(session)

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)

# =============================================================================
# TEST 1: Questionnaire Versioning & Clinician Publishing Authorization
# =============================================================================

def test_questionnaire_versioning_and_clinician_approval(db):
    admin = db.query(User).filter(User.role == RoleEnum.ADMIN).first()
    clinician = db.query(User).filter(User.role == RoleEnum.CLINICIAN).first()

    # Admin creates new draft version v1.1.0
    new_v = QuestionnaireService.create_version(
        db,
        QuestionnaireVersionCreate(
            version_tag="v1.1.0-draft",
            title_en="GENOVEX Questionnaire v1.1.0 (Draft)",
            title_ar="استبيان جينوفيكس v1.1.0 (مسودة)"
        ),
        user=admin
    )
    assert new_v.status == QuestionnaireStatus.DRAFT

    # Admin adds a custom question with clinical rationale
    q = QuestionnaireService.add_question(
        db,
        QuestionCreate(
            version_id=new_v.id,
            domain_code=QuestionDomain.LIFESTYLE_HABITS,
            question_key="Q_TEST_SAUNA",
            text_en="Do you use a hot sauna more than 3 times a week?",
            text_ar="هل تستخدم الساونا الحارة أكثر من 3 مرات أسبوعياً؟",
            question_type=QuestionType.SINGLE_CHOICE,
            options_json=[
                QuestionOptionSchema(key="yes", label_en="Yes", label_ar="نعم", order=1),
                QuestionOptionSchema(key="no", label_en="No", label_ar="لا", order=2)
            ],
            clinical_rationale_en="Thermal stress damages testicular spermatogenesis.",
            clinical_rationale_ar="الإجهاد الحراري يضر بتكوين الحيوانات المنوية.",
            evidence_references=["AUA Guidelines 2021"]
        ),
        user=admin
    )
    assert q.id is not None
    assert q.question_key == "Q_TEST_SAUNA"

    # Non-clinician (Admin) attempts to publish -> must raise HTTP 403 Forbidden
    with pytest.raises(HTTPException) as exc_info:
        QuestionnaireService.publish_version(db, version_id=new_v.id, user=admin)
    assert exc_info.value.status_code == 403

    # Authorized Clinician publishes version
    published_v = QuestionnaireService.publish_version(
        db, version_id=new_v.id, user=clinician, notes="Clinically approved for production trial"
    )
    assert published_v.status == QuestionnaireStatus.PUBLISHED
    assert published_v.published_at is not None
    assert published_v.clinical_reviewer_id == clinician.id

# =============================================================================
# TEST 2: Start Assessment & Version Pinning
# =============================================================================

def test_start_assessment_version_pinning(db):
    patient = db.query(User).filter(User.role == RoleEnum.PATIENT).first()

    # Start assessment session
    start_resp = QuestionnaireService.start_or_resume_assessment(db, user=patient)
    assert start_resp.assessment_id is not None
    assert start_resp.version_tag == "v1.0.0"
    assert start_resp.total_domains == 11
    assert start_resp.current_domain_index == 0

    # Ensure assessment in database is pinned to v1.0.0
    assessment = db.query(Assessment).filter(Assessment.id == start_resp.assessment_id).first()
    pinned_version_id = assessment.questionnaire_version_id

    # If an admin now publishes v2.0.0, the existing assessment must remain pinned to v1.0.0
    clinician = db.query(User).filter(User.role == RoleEnum.CLINICIAN).first()
    new_v = QuestionnaireService.create_version(
        db,
        QuestionnaireVersionCreate(version_tag="v2.0.0", title_en="v2.0.0", title_ar="v2.0.0")
    )
    QuestionnaireService.publish_version(db, version_id=new_v.id, user=clinician)

    # Resume the existing assessment: must stay pinned to v1.0.0!
    resumed = QuestionnaireService.start_or_resume_assessment(db, session_token=start_resp.session_token)
    assert resumed.questionnaire_version_id == pinned_version_id
    assert resumed.version_tag == "v1.0.0"

# =============================================================================
# TEST 3: Dynamic Conditional Follow-Up Branching
# =============================================================================

def test_dynamic_conditional_branching(db):
    start = QuestionnaireService.start_or_resume_assessment(db)
    assessment_id = start.assessment_id

    # Domain 2 is TESTICULAR_HISTORY (index 2)
    # Initially, Q_TESTIS_SURGERY is visible, but Q_TESTIS_SURGERY_TYPE must be hidden!
    domain_q = QuestionnaireService.get_domain_questions(db, assessment_id=assessment_id, domain_index=2)
    keys_initial = [q.question_key for q in domain_q.questions]
    assert "Q_TESTIS_SURGERY" in keys_initial
    assert "Q_TESTIS_SURGERY_TYPE" not in keys_initial  # Hidden because surgery was not answered "yes"

    # User answers "no" to surgery
    q_surg = next(q for q in domain_q.questions if q.question_key == "Q_TESTIS_SURGERY")
    QuestionnaireService.save_domain_responses(
        db, assessment_id=assessment_id,
        data=SaveDomainResponsesRequest(
            domain_code=QuestionDomain.TESTICULAR_HISTORY,
            answers=[AnswerInput(question_id=q_surg.id, question_key=q_surg.question_key, answer_value="no")]
        )
    )

    # Re-fetch: follow-up Q_TESTIS_SURGERY_TYPE must still be hidden
    domain_q_after_no = QuestionnaireService.get_domain_questions(db, assessment_id=assessment_id, domain_index=2)
    assert "Q_TESTIS_SURGERY_TYPE" not in [q.question_key for q in domain_q_after_no.questions]

    # User changes answer to "yes" for surgery
    QuestionnaireService.save_domain_responses(
        db, assessment_id=assessment_id,
        data=SaveDomainResponsesRequest(
            domain_code=QuestionDomain.TESTICULAR_HISTORY,
            answers=[AnswerInput(question_id=q_surg.id, question_key=q_surg.question_key, answer_value="yes")]
        )
    )

    # Re-fetch: Q_TESTIS_SURGERY_TYPE must dynamically appear!
    domain_q_after_yes = QuestionnaireService.get_domain_questions(db, assessment_id=assessment_id, domain_index=2)
    keys_after_yes = [q.question_key for q in domain_q_after_yes.questions]
    assert "Q_TESTIS_SURGERY_TYPE" in keys_after_yes

# =============================================================================
# TEST 4: Safe Answers: "Unsure" and "Prefer not to answer" Never Count as Negative
# =============================================================================

def test_safe_unsure_and_prefer_not_to_say(db):
    start = QuestionnaireService.start_or_resume_assessment(db)
    assessment_id = start.assessment_id

    # Fetch Domain 0 (Basic Health)
    domain_q = QuestionnaireService.get_domain_questions(db, assessment_id=assessment_id, domain_index=0)
    q_bmi = next(q for q in domain_q.questions if q.question_key == "Q_BMI_CATEGORY")

    # User selects "Unsure"
    QuestionnaireService.save_domain_responses(
        db, assessment_id=assessment_id,
        data=SaveDomainResponsesRequest(
            domain_code=QuestionDomain.BASIC_HEALTH,
            answers=[AnswerInput(question_id=q_bmi.id, question_key=q_bmi.question_key, answer_value=None, is_unsure=True)]
        )
    )

    saved_resp = db.query(AssessmentResponse).filter(
        AssessmentResponse.assessment_id == assessment_id,
        AssessmentResponse.question_key == "Q_BMI_CATEGORY"
    ).first()

    assert saved_resp is not None
    assert saved_resp.is_unsure == True
    assert saved_resp.answer_value is None

    # Review screen verification: Unsure counts as answered, NOT as a negative or missing value
    review = QuestionnaireService.get_assessment_review(db, assessment_id=assessment_id)
    review_q = next(
        q for d in review.domains for q in d.questions if q.question_key == "Q_BMI_CATEGORY"
    )
    assert review_q.is_answered == True
    assert review_q.is_unsure == True

# =============================================================================
# TEST 5: Deterministic Urgent Red-Flag Safety Circuit
# =============================================================================

def test_deterministic_urgent_safety_circuit(db):
    start = QuestionnaireService.start_or_resume_assessment(db)
    assessment_id = start.assessment_id

    # Fetch Domain 2 (Testicular History)
    domain_q = QuestionnaireService.get_domain_questions(db, assessment_id=assessment_id, domain_index=2)
    q_pain = next(q for q in domain_q.questions if q.question_key == "Q_ACUTE_SCROTAL_PAIN")
    assert q_pain.is_urgent_red_flag == True

    # User answers "yes" to acute scrotal pain
    save_resp = QuestionnaireService.save_domain_responses(
        db, assessment_id=assessment_id,
        data=SaveDomainResponsesRequest(
            domain_code=QuestionDomain.TESTICULAR_HISTORY,
            answers=[AnswerInput(question_id=q_pain.id, question_key=q_pain.question_key, answer_value="yes")]
        )
    )

    # Verify urgent alert is detected immediately in response
    assert "Q_ACUTE_SCROTAL_PAIN" in save_resp.urgent_red_flags_detected

    # Review screen flags urgent red-flag
    review = QuestionnaireService.get_assessment_review(db, assessment_id=assessment_id)
    assert "Q_ACUTE_SCROTAL_PAIN" in review.urgent_red_flags

    # Upon submission: Deterministic emergency warning generated WITHOUT any AI hallucination
    submit_res = QuestionnaireService.submit_assessment(db, assessment_id=assessment_id)
    assert submit_res.has_urgent_red_flags == True
    assert "URGENT CLINICAL ALERT" in submit_res.urgent_warning_en
    assert "تنبيه سريري عاجل" in submit_res.urgent_warning_ar
    assert submit_res.status == AssessmentStatus.LOCKED
