import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone
from fastapi import HTTPException

from app.core.database import Base
from app.models.clinical_rules import ClinicalRule, ClinicalOutcomeTier, ClinicalRuleStatus
from app.models.medical_content import (
    PublicationStatus, MedicalCategory, MedicalReference,
    MedicalCondition, ConditionContent, ContentVersion, ClinicalReviewRecord
)
from app.core.security import User, AuditLog, RoleEnum, get_password_hash
from app.schemas.medical_content import (
    MedicalConditionCreate, MedicalConditionUpdate, ConditionContentSchema,
    ClinicalReviewActionRequest, RestoreVersionRequest
)
from app.services.medical_content_service import MedicalContentService

# In-memory SQLite for high-speed, isolated unit and integration testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    
    # 0. Seed Users with Distinct Roles
    admin_user = User(
        email="admin@test.health",
        hashed_password=get_password_hash("AdminPass123"),
        full_name="Sarah Jenkins",
        role=RoleEnum.ADMIN,
        credentials_summary="Content Operations Lead"
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

    # 1. Seed Category
    cat = MedicalCategory(
        slug="test-endocrine",
        name_en="Test Endocrine Category",
        name_ar="فئة الغدد الصماء الاختبارية",
        display_order=1
    )
    # 2. Seed Reference
    ref = MedicalReference(
        title="WHO Semen Manual 6th Edition",
        guideline_body="WHO",
        evidence_classification="Guideline Consensus",
        publication_year=2021
    )
    # 3. Seed Clinical Rule to verify architectural decoupling
    rule = ClinicalRule(
        rule_code="R-TEST-VARICO-01",
        name="Clinical Varicocele Triaging Rule",
        target_condition_slug="varicocele",
        outcome_tier=ClinicalOutcomeTier.TIER_3_EVAL_RECOMMENDED,
        priority_rank=20,
        trigger_criteria={"symptoms": ["dull_scrotal_ache"], "palpable_mass": True},
        clinical_rationale_en="Clinical varicocele with symptoms warrants reproductive urologist evaluation.",
        clinical_rationale_ar="دوالي الخصية السريرية المصحوبة بأعراض تستدعي تقييماً سريرياً.",
        guideline_source="EAU Male Infertility Guidelines 2024",
        status=ClinicalRuleStatus.ACTIVE
    )
    session.add_all([cat, ref, rule])
    session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)

# =============================================================================
# TEST 1: Creation of Condition with 20 Structured Fields & Bilingual Content
# =============================================================================

def test_create_condition_with_bilingual_structured_fields(db):
    cat = db.query(MedicalCategory).first()
    ref = db.query(MedicalReference).first()
    admin_user = db.query(User).filter(User.role == RoleEnum.ADMIN).first()

    payload = MedicalConditionCreate(
        slug="azoospermia-test",
        category_id=cat.id,
        organs_involved=["Testes", "Epididymis"],
        evidence_classification="Level 1A",
        reference_ids=[ref.id],
        en_content=ConditionContentSchema(
            language="en",
            name="Non-Obstructive Azoospermia",
            short_description="Absence of spermatozoa in the ejaculate due to intrinsic testicular failure.",
            detailed_explanation="Non-obstructive azoospermia accounts for roughly 60% of azoospermia cases.",
            biological_mechanism="Severe spermatogenic arrest or Sertoli-cell-only syndrome with high FSH.",
            causes_and_risk_factors="Genetic deletions (AZF), cryptorchidism, or gonadotoxic exposure.",
            possible_symptoms="Typically asymptomatic except for fertility difficulty.",
            silent_asymptomatic_presentation="Men possess normal virilization and normal volume ejaculate without pain.",
            clinical_significance="Requires micro-TESE or donor options; high clinical counseling importance.",
            diagnostic_investigations="Centrifuged semen analysis, serum FSH and total testosterone, karyotype.",
            clinical_next_steps="Evaluation by an Andrologist specializing in surgical sperm retrieval."
        ),
        ar_content=ConditionContentSchema(
            language="ar",
            name="انعدام الحيوانات المنوية غير الانسدادي",
            short_description="غياب تام للنطاف في السائل المنوي ناتج عن قصور أولي في نسيج الخصية.",
            detailed_explanation="يمثل انعدام النطاف غير الانسدادي حوالي 60٪ من مجمل حالات انعدام الحيوانات المنوية.",
            biological_mechanism="توقف نضوج النطاف أو متلازمة خلايا سيرتولي فقط مع ارتفاع هرمون FSH.",
            causes_and_risk_factors="طفرات الكروموسوم Y (AZF)، الخصية المعلقة، أو العلاجات السامة للخلايا.",
            possible_symptoms="لا توجد أعراض ظاهرة سوى تأخر الإنجاب.",
            silent_asymptomatic_presentation="يمتلك الرجل مظهراً ذكورياً طبيعياً وحجم سائل طبيعي تماماً دون ألم.",
            clinical_significance="يتطلب إجراء مسح مجهري للخصية (micro-TESE) لاستخلاص الحيوانات المنوية.",
            diagnostic_investigations="تحليل السائل المنوي بالطرد المركزي، هرمون FSH والتستوستيرون، وفحص الكروموسومات.",
            clinical_next_steps="استشارة استشاري طب وجراحة الذكورة المتخصص في المسح المجهري."
        ),
        initial_status=PublicationStatus.DRAFT,
        created_by=admin_user.full_name
    )

    cond = MedicalContentService.create_condition(db, payload, user=admin_user)
    assert cond.id is not None
    assert cond.slug == "azoospermia-test"
    assert cond.publication_status == PublicationStatus.DRAFT
    assert cond.current_version == 1
    assert len(cond.contents) == 2
    assert len(cond.references) == 1

    # Verify initial ContentVersion snapshot was created
    versions = MedicalContentService.get_version_history(db, cond.id)
    assert len(versions) == 1
    assert versions[0].version_number == 1
    assert versions[0].snapshot_data["slug"] == "azoospermia-test"

    # Verify Security Audit Log was created
    audit = db.query(AuditLog).filter(AuditLog.action == "CREATE_CONDITION").first()
    assert audit is not None
    assert audit.user_email == admin_user.email
    assert audit.user_role == "ADMIN"

# =============================================================================
# TEST 2: Decoupling: Drafts Must NOT Appear in Public Health Library
# =============================================================================

def test_draft_not_visible_in_public_health_library(db):
    test_create_condition_with_bilingual_structured_fields(db)

    public_items_en = MedicalContentService.get_public_health_library(db, language="en")
    assert len(public_items_en) == 0  # DRAFT is not public!

    public_items_ar = MedicalContentService.get_public_health_library(db, language="ar")
    assert len(public_items_ar) == 0

# =============================================================================
# TEST 3: RBAC Enforcement: Unauthorized Users Cannot Approve or Publish
# =============================================================================

def test_rbac_unauthorized_user_cannot_approve_or_publish(db):
    test_create_condition_with_bilingual_structured_fields(db)
    cond = db.query(MedicalCondition).filter(MedicalCondition.slug == "azoospermia-test").first()
    patient_user = db.query(User).filter(User.role == RoleEnum.PATIENT).first()
    admin_user = db.query(User).filter(User.role == RoleEnum.ADMIN).first()

    # Move to PENDING_REVIEW
    MedicalContentService.handle_review_action(
        db, cond.id,
        ClinicalReviewActionRequest(action="SUBMIT_FOR_REVIEW", reviewer_name="Sarah", reviewer_role="ADMIN"),
        user=admin_user
    )

    # 1. Patient attempts to APPROVE -> must raise HTTP 403
    with pytest.raises(HTTPException) as exc_info:
        MedicalContentService.handle_review_action(
            db, cond.id,
            ClinicalReviewActionRequest(action="APPROVE", reviewer_name="Patient", reviewer_role="PATIENT"),
            user=patient_user
        )
    assert exc_info.value.status_code == 403
    assert "Only verified clinical reviewers" in exc_info.value.detail

    # 2. Admin (non-clinician) attempts to PUBLISH -> must raise HTTP 403
    with pytest.raises(HTTPException) as exc_info2:
        MedicalContentService.handle_review_action(
            db, cond.id,
            ClinicalReviewActionRequest(action="PUBLISH", reviewer_name="Admin", reviewer_role="ADMIN"),
            user=admin_user
        )
    assert exc_info2.value.status_code == 403

# =============================================================================
# TEST 4: Authorized Clinical Review Workflow & Audit Log Capture
# =============================================================================

def test_authorized_clinical_review_workflow(db):
    test_create_condition_with_bilingual_structured_fields(db)
    cond = db.query(MedicalCondition).filter(MedicalCondition.slug == "azoospermia-test").first()
    clinician = db.query(User).filter(User.role == RoleEnum.CLINICIAN).first()
    admin = db.query(User).filter(User.role == RoleEnum.ADMIN).first()

    # 1. Submit for Review
    cond = MedicalContentService.handle_review_action(
        db, cond.id, 
        ClinicalReviewActionRequest(action="SUBMIT_FOR_REVIEW", reviewer_name=admin.full_name, reviewer_role="ADMIN"),
        user=admin
    )
    assert cond.publication_status == PublicationStatus.PENDING_REVIEW

    # 2. Rejection Test by Clinician
    cond = MedicalContentService.handle_review_action(
        db, cond.id,
        ClinicalReviewActionRequest(
            action="REJECT",
            reviewer_name=clinician.full_name,
            reviewer_role=clinician.role.value,
            notes="Please expand on Y-chromosome microdeletion testing."
        ),
        user=clinician
    )
    assert cond.publication_status == PublicationStatus.REJECTED

    # 3. Resubmit and Approve by Clinician
    MedicalContentService.handle_review_action(
        db, cond.id,
        ClinicalReviewActionRequest(action="SUBMIT_FOR_REVIEW", reviewer_name=admin.full_name, reviewer_role="ADMIN"),
        user=admin
    )
    cond = MedicalContentService.handle_review_action(
        db, cond.id,
        ClinicalReviewActionRequest(
            action="APPROVE",
            reviewer_name=clinician.full_name,
            reviewer_role=clinician.role.value,
            notes="Approved after revision per EAU 2024 guidelines."
        ),
        user=clinician
    )
    assert cond.publication_status == PublicationStatus.APPROVED

    # 4. Publish by Clinician
    cond = MedicalContentService.handle_review_action(
        db, cond.id,
        ClinicalReviewActionRequest(
            action="PUBLISH",
            reviewer_name=clinician.full_name,
            reviewer_role=clinician.role.value,
            notes="Published to live public Health Library"
        ),
        user=clinician
    )
    assert cond.publication_status == PublicationStatus.PUBLISHED
    assert cond.last_reviewed_at is not None
    assert clinician.full_name in cond.clinical_reviewer

    # Verify Audit Logs for Review Actions were recorded
    review_audits = db.query(AuditLog).filter(AuditLog.action.like("REVIEW_%")).all()
    assert len(review_audits) >= 3

    # Verify dynamically visible in public health library in EN & AR
    pub_en = MedicalContentService.get_public_health_library(db, language="en")
    assert len(pub_en) == 1
    assert pub_en[0].name == "Non-Obstructive Azoospermia"

    pub_ar = MedicalContentService.get_public_health_library(db, language="ar")
    assert len(pub_ar) == 1
    assert pub_ar[0].name == "انعدام الحيوانات المنوية غير الانسدادي"

# =============================================================================
# TEST 5: Version History & Rollback with Audit Record
# =============================================================================

def test_version_history_and_restore(db):
    test_authorized_clinical_review_workflow(db)
    cond = db.query(MedicalCondition).filter(MedicalCondition.slug == "azoospermia-test").first()
    admin = db.query(User).filter(User.role == RoleEnum.ADMIN).first()

    # Update condition to create Version 2
    update_data = MedicalConditionUpdate(
        en_content=ConditionContentSchema(
            language="en",
            name="Non-Obstructive Azoospermia (Experimental Title v2)",
            short_description="Experimental v2 short description.",
            detailed_explanation="Experimental v2 detailed explanation.",
            biological_mechanism="Experimental v2 mechanism.",
            causes_and_risk_factors="Experimental v2 causes.",
            possible_symptoms="Experimental v2 symptoms.",
            silent_asymptomatic_presentation="Experimental v2 silent alert.",
            clinical_significance="Experimental v2 significance.",
            diagnostic_investigations="Experimental v2 diagnostics.",
            clinical_next_steps="Experimental v2 next steps."
        ),
        change_summary="Modified title and clinical details for review",
        modified_by=admin.full_name
    )

    cond_v2 = MedicalContentService.update_condition(db, cond.id, update_data, user=admin)
    assert cond_v2.current_version == 2

    # Verify 2 versions in history
    versions = MedicalContentService.get_version_history(db, cond.id)
    assert len(versions) == 2

    # Restore to Version 1
    restored = MedicalContentService.restore_version(
        db, cond.id,
        RestoreVersionRequest(
            version_number=1,
            reason="Reverting experimental title back to verified baseline",
            restored_by=admin.full_name
        ),
        user=admin
    )

    # Restoration creates Version 3 to preserve complete audit history
    assert restored.current_version == 3
    en_restored = next(c for c in restored.contents if c.language == "en")
    assert en_restored.name == "Non-Obstructive Azoospermia"  # Reverted back to v1!

    # Verify rollback audit entry
    rollback_audit = db.query(AuditLog).filter(AuditLog.action == "RESTORE_VERSION").first()
    assert rollback_audit is not None
    assert rollback_audit.details["restored_from_version"] == 1
    assert rollback_audit.details["new_version"] == 3

# =============================================================================
# TEST 6: Archive Condition Traces Record but Hides from Public View
# =============================================================================

def test_archive_condition(db):
    test_authorized_clinical_review_workflow(db)
    cond = db.query(MedicalCondition).filter(MedicalCondition.slug == "azoospermia-test").first()
    admin = db.query(User).filter(User.role == RoleEnum.ADMIN).first()

    archived = MedicalContentService.handle_review_action(
        db, cond.id,
        ClinicalReviewActionRequest(action="ARCHIVE", reviewer_name=admin.full_name, reviewer_role="ADMIN"),
        user=admin
    )
    assert archived.publication_status == PublicationStatus.ARCHIVED

    # Must disappear from public health library
    pub_items = MedicalContentService.get_public_health_library(db, language="en")
    assert len(pub_items) == 0

    # Still traceable in database
    db_cond = db.query(MedicalCondition).filter(MedicalCondition.slug == "azoospermia-test").first()
    assert db_cond is not None
    assert db_cond.publication_status == PublicationStatus.ARCHIVED

# =============================================================================
# TEST 7: Strict Architectural Boundary: Rule Engine Remains Untouched
# =============================================================================

def test_architectural_separation_rule_engine_untouched(db):
    rule = db.query(ClinicalRule).filter(ClinicalRule.rule_code == "R-TEST-VARICO-01").first()
    original_criteria = rule.trigger_criteria
    original_tier = rule.outcome_tier
    original_version = rule.rule_version

    # Perform extensive condition edits, additions and rollbacks
    test_version_history_and_restore(db)

    # Verify ClinicalRule state is 100% identical and unaffected
    db.refresh(rule)
    assert rule.trigger_criteria == original_criteria
    assert rule.outcome_tier == original_tier
    assert rule.rule_version == original_version
    assert rule.status == ClinicalRuleStatus.ACTIVE
