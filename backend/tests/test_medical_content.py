import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

from app.core.database import Base
from app.models.clinical_rules import ClinicalRule, ClinicalOutcomeTier, ClinicalRuleStatus
from app.models.medical_content import (
    PublicationStatus, MedicalCategory, MedicalReference,
    MedicalCondition, ConditionContent, ContentVersion, ClinicalReviewRecord
)
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
        created_by="Dr. Sarah Al-Ali"
    )

    cond = MedicalContentService.create_condition(db, payload)
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

# =============================================================================
# TEST 2: Decoupling: Drafts Must NOT Appear in Public Health Library
# =============================================================================

def test_draft_not_visible_in_public_health_library(db):
    test_create_condition_with_bilingual_structured_fields(db)

    # Query public health library
    public_items_en = MedicalContentService.get_public_health_library(db, language="en")
    assert len(public_items_en) == 0  # DRAFT is not public!

    public_items_ar = MedicalContentService.get_public_health_library(db, language="ar")
    assert len(public_items_ar) == 0

# =============================================================================
# TEST 3: Clinical Review Workflow (Submit -> Review -> Approve -> Publish)
# =============================================================================

def test_full_clinical_review_workflow(db):
    test_create_condition_with_bilingual_structured_fields(db)
    cond = db.query(MedicalCondition).filter(MedicalCondition.slug == "azoospermia-test").first()

    # 1. Submit for Review
    cond = MedicalContentService.handle_review_action(
        db, cond.id, 
        ClinicalReviewActionRequest(
            action="SUBMIT_FOR_REVIEW",
            reviewer_name="Dr. Sarah Al-Ali",
            reviewer_role="Clinical Editor",
            notes="Submitting draft for peer review"
        )
    )
    assert cond.publication_status == PublicationStatus.PENDING_REVIEW

    # 2. Rejection Test
    cond = MedicalContentService.handle_review_action(
        db, cond.id,
        ClinicalReviewActionRequest(
            action="REJECT",
            reviewer_name="Dr. Ahmed Mansour",
            reviewer_role="Consultant Andrologist (DHA)",
            notes="Please expand on Y-chromosome microdeletion testing."
        )
    )
    assert cond.publication_status == PublicationStatus.REJECTED

    # 3. Resubmit and Approve
    MedicalContentService.handle_review_action(
        db, cond.id,
        ClinicalReviewActionRequest(
            action="SUBMIT_FOR_REVIEW",
            reviewer_name="Dr. Sarah Al-Ali",
            reviewer_role="Clinical Editor"
        )
    )
    cond = MedicalContentService.handle_review_action(
        db, cond.id,
        ClinicalReviewActionRequest(
            action="APPROVE",
            reviewer_name="Dr. Ahmed Mansour",
            reviewer_role="Consultant Andrologist (DHA)",
            notes="Approved after revision per EAU 2024 guidelines."
        )
    )
    assert cond.publication_status == PublicationStatus.APPROVED

    # 4. Publish
    cond = MedicalContentService.handle_review_action(
        db, cond.id,
        ClinicalReviewActionRequest(
            action="PUBLISH",
            reviewer_name="Dr. Ahmed Mansour",
            reviewer_role="Consultant Andrologist (DHA)",
            notes="Published to live public Health Library"
        )
    )
    assert cond.publication_status == PublicationStatus.PUBLISHED
    assert cond.last_reviewed_at is not None
    assert "Dr. Ahmed Mansour" in cond.clinical_reviewer

    # 5. Now it must be dynamically visible in public health library in EN & AR
    pub_en = MedicalContentService.get_public_health_library(db, language="en")
    assert len(pub_en) == 1
    assert pub_en[0].name == "Non-Obstructive Azoospermia"
    assert pub_en[0].language == "en"

    pub_ar = MedicalContentService.get_public_health_library(db, language="ar")
    assert len(pub_ar) == 1
    assert pub_ar[0].name == "انعدام الحيوانات المنوية غير الانسدادي"
    assert pub_ar[0].language == "ar"

# =============================================================================
# TEST 4: Version History & Rollback
# =============================================================================

def test_version_history_and_restore(db):
    test_full_clinical_review_workflow(db)
    cond = db.query(MedicalCondition).filter(MedicalCondition.slug == "azoospermia-test").first()

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
        modified_by="Dr. Sarah Al-Ali"
    )

    cond_v2 = MedicalContentService.update_condition(db, cond.id, update_data)
    assert cond_v2.current_version == 2
    en_v2 = next(c for c in cond_v2.contents if c.language == "en")
    assert en_v2.name == "Non-Obstructive Azoospermia (Experimental Title v2)"

    # Verify 2 versions in history
    versions = MedicalContentService.get_version_history(db, cond.id)
    assert len(versions) == 2

    # Restore to Version 1
    restored = MedicalContentService.restore_version(
        db, cond.id,
        RestoreVersionRequest(
            version_number=1,
            reason="Reverting experimental title back to verified baseline",
            restored_by="Lead Quality Officer"
        )
    )

    # Restoration creates Version 3 to preserve complete audit history
    assert restored.current_version == 3
    en_restored = next(c for c in restored.contents if c.language == "en")
    assert en_restored.name == "Non-Obstructive Azoospermia"  # Reverted back to v1!

# =============================================================================
# TEST 5: Archive Condition Traces Record but Hides from Public View
# =============================================================================

def test_archive_condition(db):
    test_full_clinical_review_workflow(db)
    cond = db.query(MedicalCondition).filter(MedicalCondition.slug == "azoospermia-test").first()

    # Archive condition
    archived = MedicalContentService.handle_review_action(
        db, cond.id,
        ClinicalReviewActionRequest(
            action="ARCHIVE",
            reviewer_name="Compliance Officer",
            reviewer_role="Administrator",
            notes="Archived for historical records"
        )
    )
    assert archived.publication_status == PublicationStatus.ARCHIVED

    # Must disappear from public health library
    pub_items = MedicalContentService.get_public_health_library(db, language="en")
    assert len(pub_items) == 0

    # Still traceable in database for assessment history audit
    db_cond = db.query(MedicalCondition).filter(MedicalCondition.slug == "azoospermia-test").first()
    assert db_cond is not None
    assert db_cond.publication_status == PublicationStatus.ARCHIVED

# =============================================================================
# TEST 6: Strict Architectural Boundary: Rule Engine Remains Untouched
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
