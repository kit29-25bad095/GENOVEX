from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import User, RoleEnum, get_current_user, require_roles
from app.models.medical_content import PublicationStatus, MedicalCategory, MedicalReference
from app.schemas.medical_content import (
    MedicalConditionCreate, MedicalConditionUpdate, MedicalConditionResponse,
    MedicalConditionListItem, MedicalCategoryCreate, MedicalCategoryUpdate,
    MedicalCategoryResponse, MedicalReferenceCreate, MedicalReferenceResponse,
    ClinicalReviewActionRequest, ContentVersionResponse, RestoreVersionRequest,
    ClinicalReviewRecordResponse
)
from app.services.medical_content_service import MedicalContentService

router = APIRouter(prefix="/admin/medical-content", tags=["Admin - Medical Content Management"])

# =============================================================================
# Conditions Management
# =============================================================================

@router.get("/conditions", response_model=List[MedicalConditionListItem])
def list_conditions(
    search: Optional[str] = Query(None, description="Search by name, slug or description"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    status: Optional[PublicationStatus] = Query(None, description="Filter by publication status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.CLINICIAN, RoleEnum.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Retrieve list of medical conditions with filters for admin dashboard"""
    return MedicalContentService.list_conditions(
        db, search=search, category_id=category_id, status=status, skip=skip, limit=limit
    )

@router.post("/conditions", response_model=MedicalConditionResponse)
def create_condition(
    data: MedicalConditionCreate,
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Create a new medical condition with bilingual EN/AR translations and structured clinical fields"""
    condition = MedicalContentService.create_condition(db, data, user=current_user)
    return MedicalContentService.get_condition_detail(db, condition.id)

@router.get("/conditions/{condition_id}", response_model=MedicalConditionResponse)
def get_condition(
    condition_id: int = Path(..., ge=1),
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.CLINICIAN, RoleEnum.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Retrieve complete condition detail including translations, references, version and review status"""
    return MedicalContentService.get_condition_detail(db, condition_id)

@router.put("/conditions/{condition_id}", response_model=MedicalConditionResponse)
def update_condition(
    condition_id: int = Path(..., ge=1),
    data: MedicalConditionUpdate = ...,
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Update condition content. Automatically bumps version and captures snapshot."""
    condition = MedicalContentService.update_condition(db, condition_id, data, user=current_user)
    return MedicalContentService.get_condition_detail(db, condition.id)

# =============================================================================
# Clinical Review & Publication Workflow (Role-Enforced)
# =============================================================================

@router.post("/conditions/{condition_id}/review-action", response_model=MedicalConditionResponse)
def handle_review_action(
    condition_id: int = Path(..., ge=1),
    req: ClinicalReviewActionRequest = ...,
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.CLINICIAN, RoleEnum.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """
    Execute clinical review actions with role enforcement:
    - SUBMIT_FOR_REVIEW (Admin, Clinician, Superadmin)
    - APPROVE (Strictly Clinician or Superadmin only)
    - REJECT (Strictly Clinician or Superadmin only, requires notes)
    - PUBLISH (Strictly Clinician or Superadmin only)
    - ARCHIVE (Admin, Clinician, Superadmin)
    """
    condition = MedicalContentService.handle_review_action(db, condition_id, req, user=current_user)
    return MedicalContentService.get_condition_detail(db, condition.id)

@router.get("/conditions/{condition_id}/reviews", response_model=List[ClinicalReviewRecordResponse])
def get_condition_reviews(
    condition_id: int = Path(..., ge=1),
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.CLINICIAN, RoleEnum.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Get audit trail of clinical reviews, approvals and rejections for this condition"""
    condition = MedicalContentService.get_condition_detail(db, condition_id)
    return condition.review_records

# =============================================================================
# Version History & Rollback
# =============================================================================

@router.get("/conditions/{condition_id}/versions", response_model=List[ContentVersionResponse])
def get_version_history(
    condition_id: int = Path(..., ge=1),
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.CLINICIAN, RoleEnum.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Retrieve full version history snapshots for a condition"""
    return MedicalContentService.get_version_history(db, condition_id)

@router.post("/conditions/{condition_id}/restore", response_model=MedicalConditionResponse)
def restore_version(
    condition_id: int = Path(..., ge=1),
    req: RestoreVersionRequest = ...,
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Roll back condition to a previous version snapshot with audit rationale"""
    condition = MedicalContentService.restore_version(db, condition_id, req, user=current_user)
    return MedicalContentService.get_condition_detail(db, condition.id)

# =============================================================================
# Medical Category Management
# =============================================================================

@router.get("/categories", response_model=List[MedicalCategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    return db.query(MedicalCategory).order_by(MedicalCategory.display_order).all()

@router.post("/categories", response_model=MedicalCategoryResponse)
def create_category(
    data: MedicalCategoryCreate,
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    category = MedicalCategory(**data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category

@router.put("/categories/{category_id}", response_model=MedicalCategoryResponse)
def update_category(
    category_id: int,
    data: MedicalCategoryUpdate,
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    cat = db.query(MedicalCategory).filter(MedicalCategory.id == category_id).first()
    if not cat:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Category not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(cat, k, v)
    db.commit()
    db.refresh(cat)
    return cat

# =============================================================================
# Medical Reference Management
# =============================================================================

@router.get("/references", response_model=List[MedicalReferenceResponse])
def list_references(db: Session = Depends(get_db)):
    return db.query(MedicalReference).order_by(MedicalReference.title).all()

@router.post("/references", response_model=MedicalReferenceResponse)
def create_reference(
    data: MedicalReferenceCreate,
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    ref = MedicalReference(**data.model_dump())
    db.add(ref)
    db.commit()
    db.refresh(ref)
    return ref
