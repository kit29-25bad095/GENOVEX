from typing import List, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_roles, User, RoleEnum
from app.services.clinician_portal_service import ClinicianPortalService
from app.schemas.clinician import (
    ClinicianDashboardSummaryResponse, ClinicianAssessmentDetailResponse,
    ClinicianReviewStatusUpdateRequest, ClinicianReviewStatusResponse,
    ClinicianNoteCreateRequest, ClinicianNoteItem, ClinicianAISummaryRequest
)
from app.schemas.ai import ClinicianSummaryResponse

router = APIRouter(
    prefix="/clinician",
    tags=["Clinician Decision Support Portal"],
    dependencies=[Depends(require_roles([RoleEnum.CLINICIAN, RoleEnum.ADMIN]))]
)


@router.get("/dashboard", response_model=ClinicianDashboardSummaryResponse, summary="Get clinician dashboard & queue")
def get_clinician_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([RoleEnum.CLINICIAN, RoleEnum.ADMIN]))
):
    """
    Returns dashboard overview with assessment review queue counts and sanitized patient references.
    Restricted strictly to authenticated CLINICIAN, ADMIN, and SUPERADMIN users.
    """
    return ClinicianPortalService.get_clinician_dashboard(db=db, clinician_user=current_user)


@router.get("/assessments/{assessment_id}/review", response_model=ClinicianAssessmentDetailResponse, summary="Get assessment details for clinical review")
def get_assessment_for_review(
    assessment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([RoleEnum.CLINICIAN, RoleEnum.ADMIN]))
):
    """
    Retrieves full 5-state response breakdown, conditional branch states, deterministic findings,
    and review workflow history for an assessment.
    """
    return ClinicianPortalService.get_assessment_for_review(
        db=db,
        assessment_id=assessment_id,
        clinician_user=current_user
    )


@router.post("/assessments/{assessment_id}/review-status", response_model=ClinicianReviewStatusResponse, summary="Update review workflow status")
def update_review_workflow_status(
    assessment_id: str,
    payload: ClinicianReviewStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([RoleEnum.CLINICIAN, RoleEnum.ADMIN]))
):
    """
    Transitions the review workflow state (PENDING_REVIEW, IN_REVIEW, REVIEW_COMPLETED, FURTHER_INFO_REQUIRED).
    Records an immutable audit event without mutating locked historical assessment snapshots.
    """
    return ClinicianPortalService.update_review_workflow_status(
        db=db,
        assessment_id=assessment_id,
        new_status=payload.review_status,
        notes=payload.notes,
        clinician_user=current_user
    )


@router.post("/assessments/{assessment_id}/notes", response_model=ClinicianNoteItem, status_code=status.HTTP_201_CREATED, summary="Add confidential clinician note")
def add_clinician_note(
    assessment_id: str,
    payload: ClinicianNoteCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([RoleEnum.CLINICIAN, RoleEnum.ADMIN]))
):
    """
    Records a confidential clinician internal note in the immutable audit trail.
    Strictly isolated from patient-facing access.
    """
    return ClinicianPortalService.add_clinician_note(
        db=db,
        assessment_id=assessment_id,
        note_text=payload.note_text,
        clinician_user=current_user
    )


@router.get("/assessments/{assessment_id}/notes", response_model=List[ClinicianNoteItem], summary="Get confidential clinician notes")
def get_clinician_notes(
    assessment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([RoleEnum.CLINICIAN, RoleEnum.ADMIN]))
):
    """
    Retrieves confidential clinician notes for this assessment.
    """
    return ClinicianPortalService.get_clinician_notes(
        db=db,
        assessment_id=assessment_id,
        clinician_user=current_user
    )


@router.post("/assessments/{assessment_id}/ai-summary", response_model=ClinicianSummaryResponse, summary="Generate AI synthesis for clinician review")
async def get_ai_assessment_summary(
    assessment_id: str,
    payload: Optional[ClinicianAISummaryRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([RoleEnum.CLINICIAN, RoleEnum.ADMIN]))
):
    """
    Generates an AI-synthesized clinical summary of the assessment responses and deterministic triage.
    Clearly labeled with is_ai_generated: True and non-diagnostic educational badges.
    """
    focus_areas = payload.focus_areas if payload else None
    return await ClinicianPortalService.get_ai_assessment_summary(
        db=db,
        assessment_id=assessment_id,
        focus_areas=focus_areas,
        clinician_user=current_user
    )
