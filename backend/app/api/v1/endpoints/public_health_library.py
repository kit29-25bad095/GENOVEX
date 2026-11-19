from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.medical_content import MedicalCategory
from app.schemas.medical_content import PublicHealthLibraryItem, MedicalCategoryResponse
from app.services.medical_content_service import MedicalContentService

router = APIRouter(prefix="/public/health-library", tags=["Public - Health Library"])

@router.get("", response_model=List[PublicHealthLibraryItem])
def get_published_conditions(
    language: str = Query("en", pattern="^(en|ar)$", description="Language code: en or ar"),
    category_slug: Optional[str] = Query(None, description="Filter by category slug"),
    search: Optional[str] = Query(None, description="Search term in condition name, symptoms or description"),
    db: Session = Depends(get_db)
):
    """
    User-facing endpoint: Retrieves strictly PUBLISHED medical conditions.
    Decoupled from clinical assessment engine.
    """
    return MedicalContentService.get_public_health_library(
        db, language=language, category_slug=category_slug, search=search
    )

@router.get("/categories", response_model=List[MedicalCategoryResponse])
def get_public_categories(db: Session = Depends(get_db)):
    """Retrieves active medical categories for public health library filtering"""
    return db.query(MedicalCategory).filter(MedicalCategory.is_active == True).order_by(MedicalCategory.display_order).all()

@router.get("/{slug}", response_model=PublicHealthLibraryItem)
def get_published_condition_by_slug(
    slug: str = Path(..., min_length=2),
    language: str = Query("en", pattern="^(en|ar)$"),
    db: Session = Depends(get_db)
):
    """Retrieve full details of a published condition for public education"""
    return MedicalContentService.get_public_condition_by_slug(db, slug=slug, language=language)
