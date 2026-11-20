from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_optional, get_current_user, require_roles, User, RoleEnum
from app.schemas.clinical_navigation import (
    FacilityResponse, FacilityListResponse, NavigationRecommendationResponse,
    FacilityCreateRequest, FacilityUpdateRequest
)
from app.services.clinical_navigation_service import ClinicalNavigationService

router = APIRouter(prefix="/navigation", tags=["Clinical Navigation & Provider Directory"])

@router.get("/facilities", response_model=FacilityListResponse, summary="List & filter healthcare facilities")
def list_facilities(
    specialty: Optional[str] = Query(None, description="Filter by clinical specialty (e.g., Andrology, Urology)"),
    emirate: Optional[str] = Query(None, description="Filter by UAE Emirate (e.g., DUBAI, ABU_DHABI, SHARJAH)"),
    facility_type: Optional[str] = Query(None, description="Filter by facility type"),
    has_emergency: Optional[bool] = Query(None, description="Filter for 24/7 emergency service capability"),
    is_verified: Optional[bool] = Query(None, description="Filter by official verification status"),
    search: Optional[str] = Query(None, description="Search by facility name, city, or address"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    db: Session = Depends(get_db)
):
    """
    Publicly browsable directory of specialized UAE healthcare facilities and clinics.
    Supports filtering by clinical specialty, geographic location, emergency capability, and verification status.
    """
    return ClinicalNavigationService.list_facilities(
        db=db,
        specialty=specialty,
        emirate=emirate,
        facility_type=facility_type,
        has_emergency=has_emergency,
        is_verified=is_verified,
        search=search,
        page=page,
        page_size=page_size
    )

@router.get("/facilities/{identifier}", response_model=FacilityResponse, summary="Get facility details")
def get_facility_detail(
    identifier: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves full profile, contact information, booking links, and service capabilities of a facility.
    """
    return ClinicalNavigationService.get_facility(db=db, identifier=identifier)

@router.get("/recommendations/{session_token_or_ref}", response_model=NavigationRecommendationResponse, summary="Get navigation recommendations for assessment")
def get_navigation_recommendations(
    session_token_or_ref: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Generates non-diagnostic clinical navigation recommendations matching an assessment report's recommended specialties.
    Highlights 24/7 emergency centers when urgent red flags are present.
    """
    return ClinicalNavigationService.get_recommendations_for_report(
        db=db,
        session_token_or_ref=session_token_or_ref,
        current_user=current_user
    )

@router.post("/facilities", response_model=FacilityResponse, status_code=status.HTTP_201_CREATED, summary="Create facility (Admin)")
def create_facility(
    facility_req: FacilityCreateRequest,
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Administrative creation of a new verified UAE healthcare facility."""
    return ClinicalNavigationService.create_facility(
        db=db,
        facility_req=facility_req,
        admin_user=current_user
    )

@router.put("/facilities/{facility_id}", response_model=FacilityResponse, summary="Update facility (Admin)")
def update_facility(
    facility_id: int,
    facility_req: FacilityUpdateRequest,
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Administrative update of an existing healthcare facility record."""
    return ClinicalNavigationService.update_facility(
        db=db,
        facility_id=facility_id,
        facility_req=facility_req,
        admin_user=current_user
    )
