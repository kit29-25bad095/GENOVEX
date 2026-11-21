from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.core.database import SessionLocal, Base, engine
from app.core.security import User, RoleEnum, get_password_hash
from app.models.medical_content import (
    MedicalCategory, MedicalReference, MedicalCondition, 
    ConditionContent, ContentVersion, ClinicalReviewRecord,
    PublicationStatus, EvidenceClassification
)
from app.services.medical_content_service import MedicalContentService
from app.core.condition_library_data import (
    CATEGORIES_DATA, REFERENCES_DATA, CONDITIONS_DATA
)

def seed_database(db: Session):
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    # 0. Seed System Users if not present
    if not db.query(User).first():
        print("Seeding GENOVEX System Users & Roles...")
        superadmin = User(
            email="superadmin@genovex.health",
            hashed_password=get_password_hash("SuperAdmin@2026"),
            full_name="Dr. Mansoor Al-Ketbi",
            role=RoleEnum.SUPERADMIN,
            credentials_summary="Chief Medical Officer & UAE Health Informatics Lead"
        )
        clinician = User(
            email="clinician@genovex.health",
            hashed_password=get_password_hash("Clinician@2026"),
            full_name="Dr. Tarek Al-Mansoor",
            role=RoleEnum.CLINICIAN,
            credentials_summary="Consultant Andrologist / DHA-P-00129"
        )
        admin = User(
            email="admin@genovex.health",
            hashed_password=get_password_hash("Admin@2026"),
            full_name="Sarah Jenkins",
            role=RoleEnum.ADMIN,
            credentials_summary="Clinical Content Operations Lead"
        )
        patient = User(
            email="patient@genovex.health",
            hashed_password=get_password_hash("Patient@2026"),
            full_name="Rashid Al-Nuaimi",
            role=RoleEnum.PATIENT,
            credentials_summary="Registered Health Seeker"
        )
        db.add_all([superadmin, clinician, admin, patient])
        db.commit()

    print("Seeding/Verifying GENOVEX Medical Content System...")

    # 1. Idempotent Categories
    existing_cats = {c.slug: c for c in db.query(MedicalCategory).all()}
    for c_data in CATEGORIES_DATA:
        if c_data["slug"] not in existing_cats:
            cat = MedicalCategory(**c_data)
            db.add(cat)
            db.flush()
            existing_cats[c_data["slug"]] = cat

    # 2. Idempotent References
    existing_refs = {r.title: r for r in db.query(MedicalReference).all()}
    for r_data in REFERENCES_DATA:
        if r_data["title"] not in existing_refs:
            ref = MedicalReference(**r_data)
            db.add(ref)
            db.flush()
            existing_refs[r_data["title"]] = ref

    # 3. Idempotent Conditions (Preserving existing conditions, adding candidate expansions)
    existing_conds = {c.slug: c for c in db.query(MedicalCondition).all()}
    for cond_data in CONDITIONS_DATA:
        slug = cond_data["slug"]
        if slug in existing_conds:
            continue

        cat = existing_cats[cond_data["category_slug"]]
        pub_status = PublicationStatus(cond_data["publication_status"])

        condition = MedicalCondition(
            slug=slug,
            category_id=cat.id,
            organs_involved=cond_data["organs_involved"],
            evidence_classification=cond_data["evidence_classification"],
            publication_status=pub_status,
            current_version=cond_data.get("current_version", 1),
            last_reviewed_at=cond_data.get("last_reviewed_at"),
            clinical_reviewer=cond_data.get("clinical_reviewer")
        )

        condition.references = [
            existing_refs[t] for t in cond_data["reference_titles"]
            if t in existing_refs
        ]
        db.add(condition)
        db.flush()

        en_content = ConditionContent(
            condition_id=condition.id,
            language="en",
            **cond_data["en"]
        )
        ar_content = ConditionContent(
            condition_id=condition.id,
            language="ar",
            **cond_data["ar"]
        )
        db.add_all([en_content, ar_content])
        db.flush()

        v1 = ContentVersion(
            condition_id=condition.id,
            version_number=1,
            snapshot_data=MedicalContentService._create_snapshot(condition),
            change_summary="Initial clinical synthesis and bilingual documentation",
            created_by=cond_data.get("clinical_reviewer") or "Medical Content Editorial Team"
        )
        db.add(v1)
        if cond_data.get("current_version", 1) >= 2:
            v2 = ContentVersion(
                condition_id=condition.id,
                version_number=2,
                snapshot_data=MedicalContentService._create_snapshot(condition),
                change_summary="Updated ultrasound diagnostic thresholds per EAU 2024 guidelines",
                created_by=cond_data.get("clinical_reviewer") or "Medical Content Editorial Team"
            )
            db.add(v2)

        review_record = ClinicalReviewRecord(
            condition_id=condition.id,
            version_number=1,
            reviewer_name=cond_data.get("clinical_reviewer") or "Medical Content Editorial Team",
            reviewer_role="Clinical Specialist" if cond_data.get("clinical_reviewer") else "Editorial Submitter",
            action="INITIAL_SEED" if pub_status == PublicationStatus.PUBLISHED else "SUBMIT_FOR_REVIEW",
            notes=(
                "Baseline published clinical condition"
                if pub_status == PublicationStatus.PUBLISHED
                else "Synthesized from clinical practice guidelines (EAU/AUA/WHO/Endocrine Society). Pending qualified UAE clinical board review before publication."
            )
        )
        db.add(review_record)
        existing_conds[slug] = condition

    db.commit()
    print("GENOVEX Medical Content System successfully synchronized!")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
