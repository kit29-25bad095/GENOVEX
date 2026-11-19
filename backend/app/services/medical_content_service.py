from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, desc
from fastapi import HTTPException, status

from app.models.medical_content import (
    MedicalCondition, ConditionContent, MedicalCategory, 
    MedicalReference, ContentVersion, ClinicalReviewRecord,
    PublicationStatus
)
from app.schemas.medical_content import (
    MedicalConditionCreate, MedicalConditionUpdate,
    MedicalCategoryCreate, MedicalCategoryUpdate,
    MedicalReferenceCreate, ClinicalReviewActionRequest,
    RestoreVersionRequest, PublicHealthLibraryItem,
    MedicalReferenceResponse
)

class MedicalContentService:

    @staticmethod
    def _create_snapshot(condition: MedicalCondition) -> Dict[str, Any]:
        """Creates an immutable, serialized JSON snapshot of a condition's full state"""
        en_content = next((c for c in condition.contents if c.language == "en"), None)
        ar_content = next((c for c in condition.contents if c.language == "ar"), None)
        
        def content_to_dict(c: Optional[ConditionContent]) -> Dict[str, Any]:
            if not c:
                return {}
            return {
                "name": c.name,
                "short_description": c.short_description,
                "detailed_explanation": c.detailed_explanation,
                "biological_mechanism": c.biological_mechanism,
                "causes_and_risk_factors": c.causes_and_risk_factors,
                "possible_symptoms": c.possible_symptoms,
                "silent_asymptomatic_presentation": c.silent_asymptomatic_presentation,
                "clinical_significance": c.clinical_significance,
                "diagnostic_investigations": c.diagnostic_investigations,
                "clinical_next_steps": c.clinical_next_steps,
            }

        return {
            "id": condition.id,
            "slug": condition.slug,
            "category_id": condition.category_id,
            "organs_involved": condition.organs_involved or [],
            "evidence_classification": condition.evidence_classification,
            "publication_status": condition.publication_status.value,
            "version_number": condition.current_version,
            "reference_ids": [r.id for r in condition.references],
            "en_content": content_to_dict(en_content),
            "ar_content": content_to_dict(ar_content),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    # =========================================================================
    # Condition Management
    # =========================================================================

    @classmethod
    def create_condition(cls, db: Session, data: MedicalConditionCreate) -> MedicalCondition:
        # Check slug uniqueness
        existing = db.query(MedicalCondition).filter(MedicalCondition.slug == data.slug).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Condition with slug '{data.slug}' already exists")

        # Verify category exists
        category = db.query(MedicalCategory).filter(MedicalCategory.id == data.category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="Medical category not found")

        # Create condition
        condition = MedicalCondition(
            slug=data.slug,
            category_id=data.category_id,
            organs_involved=data.organs_involved,
            evidence_classification=data.evidence_classification,
            publication_status=data.initial_status,
            current_version=1
        )

        # Associate references
        if data.reference_ids:
            refs = db.query(MedicalReference).filter(MedicalReference.id.in_(data.reference_ids)).all()
            condition.references = refs

        db.add(condition)
        db.flush()

        # Add bilingual translated contents
        en_row = ConditionContent(
            condition_id=condition.id,
            language="en",
            **data.en_content.model_dump(exclude={"language"})
        )
        ar_row = ConditionContent(
            condition_id=condition.id,
            language="ar",
            **data.ar_content.model_dump(exclude={"language"})
        )
        db.add_all([en_row, ar_row])
        db.flush()

        # Create initial Version 1 snapshot
        snapshot = cls._create_snapshot(condition)
        v1 = ContentVersion(
            condition_id=condition.id,
            version_number=1,
            snapshot_data=snapshot,
            change_summary="Initial condition creation",
            created_by=data.created_by
        )
        db.add(v1)

        # Log creation review record
        review_log = ClinicalReviewRecord(
            condition_id=condition.id,
            version_number=1,
            reviewer_name=data.created_by,
            reviewer_role="Administrator",
            action="INITIAL_CREATION",
            notes="Initial draft condition created with bilingual content"
        )
        db.add(review_log)

        db.commit()
        db.refresh(condition)
        return condition

    @classmethod
    def update_condition(cls, db: Session, condition_id: int, data: MedicalConditionUpdate) -> MedicalCondition:
        condition = db.query(MedicalCondition).options(
            joinedload(MedicalCondition.contents),
            joinedload(MedicalCondition.references),
            joinedload(MedicalCondition.category)
        ).filter(MedicalCondition.id == condition_id).first()

        if not condition:
            raise HTTPException(status_code=404, detail="Medical condition not found")

        # Update primary fields
        if data.slug is not None and data.slug != condition.slug:
            slug_exists = db.query(MedicalCondition).filter(
                MedicalCondition.slug == data.slug,
                MedicalCondition.id != condition_id
            ).first()
            if slug_exists:
                raise HTTPException(status_code=400, detail="Slug already in use")
            condition.slug = data.slug

        if data.category_id is not None:
            cat = db.query(MedicalCategory).filter(MedicalCategory.id == data.category_id).first()
            if not cat:
                raise HTTPException(status_code=404, detail="Medical category not found")
            condition.category_id = data.category_id

        if data.organs_involved is not None:
            condition.organs_involved = data.organs_involved

        if data.evidence_classification is not None:
            condition.evidence_classification = data.evidence_classification

        if data.reference_ids is not None:
            refs = db.query(MedicalReference).filter(MedicalReference.id.in_(data.reference_ids)).all()
            condition.references = refs

        # Update English translation
        if data.en_content is not None:
            en_row = next((c for c in condition.contents if c.language == "en"), None)
            if en_row:
                for k, v in data.en_content.model_dump(exclude={"language"}).items():
                    setattr(en_row, k, v)
            else:
                db.add(ConditionContent(
                    condition_id=condition.id,
                    language="en",
                    **data.en_content.model_dump(exclude={"language"})
                ))

        # Update Arabic translation
        if data.ar_content is not None:
            ar_row = next((c for c in condition.contents if c.language == "ar"), None)
            if ar_row:
                for k, v in data.ar_content.model_dump(exclude={"language"}).items():
                    setattr(ar_row, k, v)
            else:
                db.add(ConditionContent(
                    condition_id=condition.id,
                    language="ar",
                    **data.ar_content.model_dump(exclude={"language"})
                ))

        # Increment version and capture snapshot
        condition.current_version += 1
        condition.updated_at = datetime.now(timezone.utc)
        
        # If published, moving to modified sets status to DRAFT or PENDING_REVIEW unless already published
        if condition.publication_status == PublicationStatus.PUBLISHED:
            condition.publication_status = PublicationStatus.PENDING_REVIEW

        db.flush()

        snapshot = cls._create_snapshot(condition)
        version_entry = ContentVersion(
            condition_id=condition.id,
            version_number=condition.current_version,
            snapshot_data=snapshot,
            change_summary=data.change_summary or "Updated condition content",
            created_by=data.modified_by
        )
        db.add(version_entry)

        # Log change
        log = ClinicalReviewRecord(
            condition_id=condition.id,
            version_number=condition.current_version,
            reviewer_name=data.modified_by,
            reviewer_role="Content Editor",
            action="UPDATE_CONTENT",
            notes=data.change_summary
        )
        db.add(log)

        db.commit()
        db.refresh(condition)
        return condition

    @classmethod
    def list_conditions(
        cls, 
        db: Session, 
        search: Optional[str] = None,
        category_id: Optional[int] = None,
        status: Optional[PublicationStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        query = db.query(MedicalCondition).options(
            joinedload(MedicalCondition.category),
            joinedload(MedicalCondition.contents),
            joinedload(MedicalCondition.references)
        )

        if category_id:
            query = query.filter(MedicalCondition.category_id == category_id)

        if status:
            query = query.filter(MedicalCondition.publication_status == status)

        if search:
            search_fmt = f"%{search.strip().lower()}%"
            query = query.join(MedicalCondition.contents).filter(
                or_(
                    MedicalCondition.slug.ilike(search_fmt),
                    ConditionContent.name.ilike(search_fmt),
                    ConditionContent.short_description.ilike(search_fmt)
                )
            ).distinct()

        conditions = query.order_by(desc(MedicalCondition.updated_at)).offset(skip).limit(limit).all()

        results = []
        for cond in conditions:
            en_c = next((c for c in cond.contents if c.language == "en"), None)
            ar_c = next((c for c in cond.contents if c.language == "ar"), None)
            results.append({
                "id": cond.id,
                "slug": cond.slug,
                "category_id": cond.category_id,
                "category_name_en": cond.category.name_en if cond.category else "",
                "category_name_ar": cond.category.name_ar if cond.category else "",
                "name_en": en_c.name if en_c else cond.slug,
                "name_ar": ar_c.name if ar_c else cond.slug,
                "short_description_en": en_c.short_description if en_c else "",
                "short_description_ar": ar_c.short_description if ar_c else "",
                "organs_involved": cond.organs_involved or [],
                "evidence_classification": cond.evidence_classification,
                "publication_status": cond.publication_status,
                "current_version": cond.current_version,
                "last_reviewed_at": cond.last_reviewed_at,
                "clinical_reviewer": cond.clinical_reviewer,
                "references_count": len(cond.references),
                "updated_at": cond.updated_at
            })
        return results

    @classmethod
    def get_condition_detail(cls, db: Session, condition_id: int) -> MedicalCondition:
        cond = db.query(MedicalCondition).options(
            joinedload(MedicalCondition.category),
            joinedload(MedicalCondition.contents),
            joinedload(MedicalCondition.references),
            joinedload(MedicalCondition.versions),
            joinedload(MedicalCondition.review_records)
        ).filter(MedicalCondition.id == condition_id).first()

        if not cond:
            raise HTTPException(status_code=404, detail="Condition not found")
        return cond

    # =========================================================================
    # Clinical Workflow: Submit, Review, Approve, Reject, Publish, Archive
    # =========================================================================

    @classmethod
    def handle_review_action(
        cls, db: Session, condition_id: int, req: ClinicalReviewActionRequest
    ) -> MedicalCondition:
        condition = cls.get_condition_detail(db, condition_id)
        action = req.action.upper()

        if action == "SUBMIT_FOR_REVIEW":
            if condition.publication_status in [PublicationStatus.PUBLISHED, PublicationStatus.ARCHIVED]:
                raise HTTPException(status_code=400, detail=f"Cannot submit condition with status {condition.publication_status}")
            condition.publication_status = PublicationStatus.PENDING_REVIEW

        elif action == "APPROVE":
            if condition.publication_status != PublicationStatus.PENDING_REVIEW:
                raise HTTPException(status_code=400, detail="Only conditions pending review can be approved")
            condition.publication_status = PublicationStatus.APPROVED
            condition.clinical_reviewer = f"{req.reviewer_name} ({req.reviewer_role})"
            condition.last_reviewed_at = datetime.now(timezone.utc)

        elif action == "REJECT":
            if condition.publication_status != PublicationStatus.PENDING_REVIEW:
                raise HTTPException(status_code=400, detail="Only conditions pending review can be rejected")
            if not req.notes:
                raise HTTPException(status_code=400, detail="Clinical rejection requires detailed feedback notes")
            condition.publication_status = PublicationStatus.REJECTED
            condition.clinical_reviewer = f"{req.reviewer_name} ({req.reviewer_role})"
            condition.last_reviewed_at = datetime.now(timezone.utc)

        elif action == "PUBLISH":
            if condition.publication_status not in [PublicationStatus.APPROVED, PublicationStatus.PENDING_REVIEW, PublicationStatus.DRAFT]:
                raise HTTPException(status_code=400, detail=f"Cannot publish from status {condition.publication_status}")
            condition.publication_status = PublicationStatus.PUBLISHED
            condition.clinical_reviewer = f"{req.reviewer_name} ({req.reviewer_role})"
            condition.last_reviewed_at = datetime.now(timezone.utc)

        elif action == "ARCHIVE":
            condition.publication_status = PublicationStatus.ARCHIVED

        elif action == "SAVE_DRAFT":
            condition.publication_status = PublicationStatus.DRAFT

        else:
            raise HTTPException(status_code=400, detail=f"Unknown clinical review action: {req.action}")

        condition.updated_at = datetime.now(timezone.utc)

        # Record review audit log
        log = ClinicalReviewRecord(
            condition_id=condition.id,
            version_number=condition.current_version,
            reviewer_name=req.reviewer_name,
            reviewer_role=req.reviewer_role,
            action=action,
            notes=req.notes
        )
        db.add(log)

        # Update latest snapshot with new publication status
        latest_version = db.query(ContentVersion).filter(
            ContentVersion.condition_id == condition.id,
            ContentVersion.version_number == condition.current_version
        ).first()
        if latest_version:
            latest_version.snapshot_data = cls._create_snapshot(condition)

        db.commit()
        db.refresh(condition)
        return condition

    # =========================================================================
    # Version History & Rollback
    # =========================================================================

    @classmethod
    def get_version_history(cls, db: Session, condition_id: int) -> List[ContentVersion]:
        cls.get_condition_detail(db, condition_id)  # verify existence
        return db.query(ContentVersion).filter(
            ContentVersion.condition_id == condition_id
        ).order_by(desc(ContentVersion.version_number)).all()

    @classmethod
    def restore_version(cls, db: Session, condition_id: int, req: RestoreVersionRequest) -> MedicalCondition:
        condition = cls.get_condition_detail(db, condition_id)

        target_version = db.query(ContentVersion).filter(
            ContentVersion.condition_id == condition_id,
            ContentVersion.version_number == req.version_number
        ).first()

        if not target_version:
            raise HTTPException(status_code=404, detail=f"Version {req.version_number} not found for this condition")

        snapshot = target_version.snapshot_data

        # Restore condition attributes
        if "category_id" in snapshot:
            condition.category_id = snapshot["category_id"]
        if "organs_involved" in snapshot:
            condition.organs_involved = snapshot["organs_involved"]
        if "evidence_classification" in snapshot:
            condition.evidence_classification = snapshot["evidence_classification"]
        
        # Restore references
        if "reference_ids" in snapshot and snapshot["reference_ids"]:
            refs = db.query(MedicalReference).filter(MedicalReference.id.in_(snapshot["reference_ids"])).all()
            condition.references = refs

        # Restore English translation
        if "en_content" in snapshot and snapshot["en_content"]:
            en_data = snapshot["en_content"]
            en_row = next((c for c in condition.contents if c.language == "en"), None)
            if en_row:
                for k, v in en_data.items():
                    setattr(en_row, k, v)

        # Restore Arabic translation
        if "ar_content" in snapshot and snapshot["ar_content"]:
            ar_data = snapshot["ar_content"]
            ar_row = next((c for c in condition.contents if c.language == "ar"), None)
            if ar_row:
                for k, v in ar_data.items():
                    setattr(ar_row, k, v)

        # Increment version to record rollback action
        condition.current_version += 1
        condition.publication_status = PublicationStatus.DRAFT  # Reverted version begins as draft for re-review
        condition.updated_at = datetime.now(timezone.utc)

        db.flush()

        # Capture new snapshot for the restoration version
        new_snapshot = cls._create_snapshot(condition)
        restored_v = ContentVersion(
            condition_id=condition.id,
            version_number=condition.current_version,
            snapshot_data=new_snapshot,
            change_summary=f"Restored to content from Version {req.version_number}. Reason: {req.reason}",
            created_by=req.restored_by
        )
        db.add(restored_v)

        # Log restoration in review log
        log = ClinicalReviewRecord(
            condition_id=condition.id,
            version_number=condition.current_version,
            reviewer_name=req.restored_by,
            reviewer_role="Administrator",
            action="RESTORE_VERSION",
            notes=f"Restored from version {req.version_number}. Clinical rationale: {req.reason}"
        )
        db.add(log)

        db.commit()
        db.refresh(condition)
        return condition

    # =========================================================================
    # User-Facing Health Library (Published Content Only)
    # =========================================================================

    @classmethod
    def get_public_health_library(
        cls, 
        db: Session, 
        language: str = "en", 
        category_slug: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[PublicHealthLibraryItem]:
        """
        Retrieves strictly PUBLISHED medical conditions for the public educational library.
        Separated from clinical assessment scoring.
        """
        query = db.query(MedicalCondition).options(
            joinedload(MedicalCondition.category),
            joinedload(MedicalCondition.contents),
            joinedload(MedicalCondition.references)
        ).filter(
            MedicalCondition.publication_status == PublicationStatus.PUBLISHED
        )

        if category_slug:
            query = query.join(MedicalCondition.category).filter(MedicalCategory.slug == category_slug)

        conditions = query.all()
        results: List[PublicHealthLibraryItem] = []

        search_term = search.lower().strip() if search else None

        for cond in conditions:
            # Find content for requested language, fall back to english
            content = next((c for c in cond.contents if c.language == language), None)
            if not content:
                content = next((c for c in cond.contents if c.language == "en"), None)
            
            if not content:
                continue

            # Apply search filter if provided
            if search_term:
                searchable_text = f"{content.name} {content.short_description} {content.detailed_explanation} {' '.join(cond.organs_involved or [])}".lower()
                if search_term not in searchable_text:
                    continue

            category_name = cond.category.name_ar if (language == "ar" and cond.category) else (cond.category.name_en if cond.category else "")

            results.append(PublicHealthLibraryItem(
                id=cond.id,
                slug=cond.slug,
                category_slug=cond.category.slug if cond.category else "",
                category_name=category_name,
                name=content.name,
                short_description=content.short_description,
                detailed_explanation=content.detailed_explanation,
                organs_involved=cond.organs_involved or [],
                biological_mechanism=content.biological_mechanism,
                causes_and_risk_factors=content.causes_and_risk_factors,
                possible_symptoms=content.possible_symptoms,
                silent_asymptomatic_presentation=content.silent_asymptomatic_presentation,
                clinical_significance=content.clinical_significance,
                diagnostic_investigations=content.diagnostic_investigations,
                clinical_next_steps=content.clinical_next_steps,
                evidence_classification=cond.evidence_classification,
                references=[
                    MedicalReferenceResponse.model_validate(r) for r in cond.references
                ],
                current_version=cond.current_version,
                last_reviewed_at=cond.last_reviewed_at,
                clinical_reviewer=cond.clinical_reviewer,
                language=language
            ))

        return results

    @classmethod
    def get_public_condition_by_slug(
        cls, db: Session, slug: str, language: str = "en"
    ) -> PublicHealthLibraryItem:
        cond = db.query(MedicalCondition).options(
            joinedload(MedicalCondition.category),
            joinedload(MedicalCondition.contents),
            joinedload(MedicalCondition.references)
        ).filter(
            MedicalCondition.slug == slug,
            MedicalCondition.publication_status == PublicationStatus.PUBLISHED
        ).first()

        if not cond:
            raise HTTPException(status_code=404, detail="Published medical condition not found in health library")

        content = next((c for c in cond.contents if c.language == language), None)
        if not content:
            content = next((c for c in cond.contents if c.language == "en"), None)

        if not content:
            raise HTTPException(status_code=404, detail="Content not available for requested language")

        category_name = cond.category.name_ar if (language == "ar" and cond.category) else (cond.category.name_en if cond.category else "")

        return PublicHealthLibraryItem(
            id=cond.id,
            slug=cond.slug,
            category_slug=cond.category.slug if cond.category else "",
            category_name=category_name,
            name=content.name,
            short_description=content.short_description,
            detailed_explanation=content.detailed_explanation,
            organs_involved=cond.organs_involved or [],
            biological_mechanism=content.biological_mechanism,
            causes_and_risk_factors=content.causes_and_risk_factors,
            possible_symptoms=content.possible_symptoms,
            silent_asymptomatic_presentation=content.silent_asymptomatic_presentation,
            clinical_significance=content.clinical_significance,
            diagnostic_investigations=content.diagnostic_investigations,
            clinical_next_steps=content.clinical_next_steps,
            evidence_classification=cond.evidence_classification,
            references=[MedicalReferenceResponse.model_validate(r) for r in cond.references],
            current_version=cond.current_version,
            last_reviewed_at=cond.last_reviewed_at,
            clinical_reviewer=cond.clinical_reviewer,
            language=language
        )
