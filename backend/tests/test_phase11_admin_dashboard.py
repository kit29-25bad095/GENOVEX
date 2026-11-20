import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.database import Base
from app.core.security import User, RoleEnum, AuditLog, get_password_hash

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
from app.models.clinical_rules import ClinicalRule, ClinicalRuleStatus, ClinicalOutcomeTier
from app.models.questionnaire import QuestionDomain
from app.models.medical_content import MedicalCondition, PublicationStatus, MedicalCategory, ContentVersion
from app.services.clinical_rule_management_service import ClinicalRuleManagementService
from app.services.medical_content_service import MedicalContentService
from app.schemas.clinical_rules import ClinicalRuleCreate, ClinicalRuleReviewAction
from app.schemas.medical_content import (
    MedicalConditionCreate, MedicalConditionUpdate, ConditionContentSchema,
    ClinicalReviewActionRequest, RestoreVersionRequest
)
from app.schemas.auth import UserUpdateRequest
from app.api.v1.endpoints.auth import update_user_role_and_status, get_all_users_admin
from fastapi import HTTPException


def test_admin_user_role_management_and_audit(db: Session):
    """
    Test Phase 11 User & Role Governance:
    - Admin can update user role, credentials, and active status
    - AuditLog records the change immutably
    - Superadmin boundary protections are enforced
    """
    # Create test actor users
    admin_actor = User(
        email="admin.tester@genovex.ae",
        full_name="Admin Tester",
        role=RoleEnum.ADMIN,
        hashed_password=get_password_hash("password123"),
        is_active=True
    )
    superadmin_actor = User(
        email="superadmin.tester@genovex.ae",
        full_name="Superadmin Tester",
        role=RoleEnum.SUPERADMIN,
        hashed_password=get_password_hash("password123"),
        is_active=True
    )
    target_user = User(
        email="dr.candidate@genovex.ae",
        full_name="Dr. Candidate",
        role=RoleEnum.PATIENT,
        hashed_password=get_password_hash("password123"),
        is_active=True
    )
    db.add_all([admin_actor, superadmin_actor, target_user])
    db.commit()

    # Mock Request for IP capture
    class MockClient:
        host = "10.0.0.1"
    class MockRequest:
        client = MockClient()

    # 1. Admin elevates patient to CLINICIAN with credentials
    update_req = UserUpdateRequest(
        role=RoleEnum.CLINICIAN,
        credentials_summary="Specialist Urologist (DHA-P-998877)",
        is_active=True
    )
    updated = update_user_role_and_status(
        user_id=target_user.id,
        req=update_req,
        request=MockRequest(),
        current_user=admin_actor,
        db=db
    )
    assert updated.role == RoleEnum.CLINICIAN
    assert updated.credentials_summary == "Specialist Urologist (DHA-P-998877)"

    # Verify AuditLog emission
    audit = db.query(AuditLog).filter(
        AuditLog.action == "UPDATE_USER_ROLE",
        AuditLog.resource_id == str(target_user.id)
    ).first()
    assert audit is not None
    assert audit.user_email == admin_actor.email
    assert audit.details["new_role"] == "CLINICIAN"

    # 2. Standard Admin cannot assign SUPERADMIN role
    illegal_req = UserUpdateRequest(role=RoleEnum.SUPERADMIN)
    with pytest.raises(HTTPException) as exc_info:
        update_user_role_and_status(
            user_id=target_user.id,
            req=illegal_req,
            request=MockRequest(),
            current_user=admin_actor,
            db=db
        )
    assert exc_info.value.status_code == 403

    # 3. Superadmin CAN assign SUPERADMIN role
    valid_superadmin_update = update_user_role_and_status(
        user_id=target_user.id,
        req=illegal_req,
        request=MockRequest(),
        current_user=superadmin_actor,
        db=db
    )
    assert valid_superadmin_update.role == RoleEnum.SUPERADMIN

    # 4. List users filtered by role
    clinicians = get_all_users_admin(role=RoleEnum.CLINICIAN, current_user=admin_actor, db=db)
    assert isinstance(clinicians, list)


def test_clinical_rule_authoring_and_approval_lifecycle(db: Session):
    """
    Test Phase 11 Clinical Rules CMS:
    - Authoring draft rule with 3-valued logic trigger
    - Submission for review
    - Clinician approval
    - Publishing to live engine and immutable snapshot creation
    """
    clinician = User(
        email="clinician.reviewer@genovex.ae",
        full_name="Dr. Reviewer",
        role=RoleEnum.CLINICIAN,
        hashed_password=get_password_hash("password123"),
        is_active=True
    )
    db.add(clinician)
    db.commit()

    # 1. Author Draft Rule
    rule_data = ClinicalRuleCreate(
        rule_code="R-TEST-PHASE11-DRAFT",
        title_en="Klinefelter Genetic Screen Pathway",
        title_ar="مسار الفحص الجيني لمتلازمة كلاينفلتر",
        domain_code=QuestionDomain.FAMILY_GENETIC,
        relevant_question_keys=["Q_KLINEFELTER_FAMILY"],
        outcome_tier=ClinicalOutcomeTier.TIER_3_EVAL_RECOMMENDED,
        is_urgent_red_flag=False,
        priority_rank=35,
        recommended_specialty="Clinical Geneticist / Reproductive Endocrinologist",
        trigger_criteria={"all_of": [{"question_key": "Q_KLINEFELTER_FAMILY", "operator": "eq", "value": "yes"}]},
        clinical_rationale_en="Azoospermia risk high in 47,XXY karyotype.",
        clinical_rationale_ar="ارتفاع خطر فقد النطاف في النمط النووي 47,XXY.",
        evidence_references=[{"title": "EAU Guidelines on Male Infertility (2024)", "year": 2024}],
        evidence_classification="Level 1b"
    )

    created_rule = ClinicalRuleManagementService.create_rule(db=db, data=rule_data, current_user=clinician)
    assert created_rule.rule_code == "R-TEST-PHASE11-DRAFT"
    assert created_rule.status == ClinicalRuleStatus.DRAFT

    # 2. Submit for review
    submitted = ClinicalRuleManagementService.submit_for_review(db=db, rule_id=created_rule.id, current_user=clinician)
    assert submitted.status == ClinicalRuleStatus.SUBMITTED_FOR_REVIEW

    # 3. Clinician Review & Approval
    review_action = ClinicalRuleReviewAction(
        action="APPROVE",
        reviewer_notes="Clinical evidence aligns with EAU Section 7 recommendations."
    )
    approved = ClinicalRuleManagementService.clinical_review(
        db=db,
        rule_id=created_rule.id,
        action=review_action,
        current_user=clinician
    )
    assert approved.status == ClinicalRuleStatus.APPROVED
    assert approved.clinical_reviewer_id == clinician.id
    assert approved.approved_at is not None

    # 4. Publish to live engine
    published = ClinicalRuleManagementService.publish_rule(db=db, rule_id=created_rule.id, current_user=clinician)
    assert published.status == ClinicalRuleStatus.PUBLISHED
    assert published.published_at is not None

    # 5. Verify version snapshot
    versions = ClinicalRuleManagementService.get_rule_versions(db=db, rule_id=created_rule.id)
    assert len(versions) >= 1
    assert versions[0].rule_code == "R-TEST-PHASE11-DRAFT"


def test_medical_content_cms_workflow_and_version_restoration(db: Session):
    """
    Test Phase 11 Medical Content CMS:
    - Create condition with bilingual fields
    - Review action workflow (SUBMIT -> APPROVE -> PUBLISH)
    - Update condition with automatic snapshot creation
    - Historical version restoration
    """
    admin = User(
        email="content.admin@genovex.ae",
        full_name="Content Admin",
        role=RoleEnum.ADMIN,
        hashed_password=get_password_hash("password123"),
        is_active=True
    )
    clinician = User(
        email="medical.director@genovex.ae",
        full_name="Medical Director",
        role=RoleEnum.CLINICIAN,
        hashed_password=get_password_hash("password123"),
        is_active=True
    )
    db.add_all([admin, clinician])
    db.commit()

    # Ensure category exists
    cat = db.query(MedicalCategory).first()
    if not cat:
        cat = MedicalCategory(slug="genetic-factors", name_en="Genetic Factors", name_ar="عوامل وراثية", display_order=1)
        db.add(cat)
        db.commit()

    # 1. Create Condition
    en_content = ConditionContentSchema(
        language="en",
        name="Y-Chromosome Microdeletion (AZF)",
        short_description="Microdeletions in AZFa, AZFb, or AZFc regions causing severe azoospermia.",
        detailed_explanation="Critical genetic screening required prior to surgical sperm retrieval.",
        biological_mechanism="Loss of DAZ and other essential spermatogenesis gene families on the Y chromosome.",
        causes_and_risk_factors="De novo microdeletions during male germ cell development.",
        possible_symptoms="Azoospermia or severe oligozoospermia with normal virilization.",
        silent_asymptomatic_presentation="Patients appear completely asymptomatic with normal secondary sexual traits.",
        clinical_significance="Guides feasibility of micro-TESE surgical sperm retrieval.",
        diagnostic_investigations="Multiplex PCR testing for AZFa, AZFb, and AZFc regions.",
        clinical_next_steps="Pre-procedure genetic counseling and reproductive andrologist evaluation."
    )
    ar_content = ConditionContentSchema(
        language="ar",
        name="الحذف الدقيق في الكروموسوم Y (AZF)",
        short_description="حذف دقيق في مناطق AZF يسبب فقد النطاف غير الانسدادي الشديد.",
        detailed_explanation="فحص وراثي دقيق مطلوب قبل عمليات استرجاع الحيوانات المنوية جراحياً.",
        biological_mechanism="فقدان جينات DAZ والجينات الضرورية لتكوين الحيوانات المنوية في الكروموسوم Y.",
        causes_and_risk_factors="طفرات حذف دقيقة جديدة تحدث أثناء تكوين الخلايا التناسلية الذكرية.",
        possible_symptoms="انعدام أو نقص حاد جداً في الحيوانات المنوية مع مظهر بدني طبيعي.",
        silent_asymptomatic_presentation="تكون الحالة غير مصحوبة بأعراض بدنية ظاهرة وتكتشف فقط بالفحص المخبري.",
        clinical_significance="تحدد إمكانية وجدوى استرجاع الحيوانات المنوية جراحياً عبر تقنية micro-TESE.",
        diagnostic_investigations="فحص تفاعل البوليميراز المتسلسل (PCR) لمناطق AZFa و AZFb و AZFc.",
        clinical_next_steps="استشارة وراثية متخصصة ومتابعة مع استشاري المسالك البولية التناسلية."
    )

    cond_in = MedicalConditionCreate(
        slug="y-chromosome-microdeletion-p11",
        category_id=cat.id,
        evidence_classification="Level 1A",
        organs_involved=["Testis", "Y Chromosome AZF Regions"],
        en_content=en_content,
        ar_content=ar_content
    )

    cond = MedicalContentService.create_condition(db=db, data=cond_in, user=admin)
    assert cond.slug == "y-chromosome-microdeletion-p11"
    assert cond.publication_status == PublicationStatus.DRAFT

    # 2. Review action: Submit -> Approve -> Publish
    MedicalContentService.handle_review_action(
        db=db,
        condition_id=cond.id,
        req=ClinicalReviewActionRequest(
            action="SUBMIT_FOR_REVIEW",
            reviewer_name=admin.full_name,
            reviewer_role=admin.role.value
        ),
        user=admin
    )
    approved_cond = MedicalContentService.handle_review_action(
        db=db,
        condition_id=cond.id,
        req=ClinicalReviewActionRequest(
            action="APPROVE",
            reviewer_name=clinician.full_name,
            reviewer_role=clinician.role.value,
            notes="Genetic criteria verified against EAU/ASRM guidelines"
        ),
        user=clinician
    )
    assert approved_cond.publication_status == PublicationStatus.APPROVED

    published_cond = MedicalContentService.handle_review_action(
        db=db,
        condition_id=cond.id,
        req=ClinicalReviewActionRequest(
            action="PUBLISH",
            reviewer_name=clinician.full_name,
            reviewer_role=clinician.role.value
        ),
        user=clinician
    )
    assert published_cond.publication_status == PublicationStatus.PUBLISHED

    # 3. Capture initial version
    initial_version = published_cond.current_version

    # 4. Update condition (should auto-bump version and snapshot)
    updated_cond = MedicalContentService.update_condition(
        db=db,
        condition_id=cond.id,
        data=MedicalConditionUpdate(
            evidence_classification="Level 1A+",
            organs_involved=["Testis", "AZFa", "AZFb", "AZFc"]
        ),
        user=admin
    )
    assert updated_cond.current_version > initial_version

    # 5. Check version snapshots
    versions = MedicalContentService.get_version_history(db=db, condition_id=cond.id)
    assert len(versions) >= 1

    # 6. Restore earlier version
    restored = MedicalContentService.restore_version(
        db=db,
        condition_id=cond.id,
        req=RestoreVersionRequest(
            version_number=versions[0].version_number,
            reason="Clinical consensus rollback",
            restored_by=admin.full_name
        ),
        user=admin
    )
    assert restored is not None
