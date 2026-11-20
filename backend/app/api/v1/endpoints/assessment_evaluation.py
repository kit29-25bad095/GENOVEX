from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.questionnaire import Assessment
from app.schemas.assessment_report import AssessmentReportResponse
from app.services.assessment_processing_service import AssessmentProcessingService
from app.core.security import get_current_user_optional, User

router = APIRouter(prefix="/assessment", tags=["Assessment Evaluation & Reports"])

@router.post("/{session_token}/evaluate", response_model=AssessmentReportResponse, summary="Evaluate assessment & compile report")
def evaluate_assessment(
    session_token: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Deterministically evaluates an assessment's responses against active clinical rules.
    Compiles an immutable AssessmentReport snapshot with evidence references and non-diagnostic explanations.
    Enforces centralized clinical governance (withholds unapproved rules across all tiers and incomplete Tier 1).
    Zero client-controlled override parameters.
    """
    assessment = db.query(Assessment).filter(Assessment.session_token == session_token).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment session not found")

    return AssessmentProcessingService.process_assessment_results(
        db=db,
        assessment_id=assessment.id,
        session_token=session_token,
        current_user=current_user
    )

@router.get("/{session_token}/report", response_model=AssessmentReportResponse, summary="Get compiled assessment report")
def get_assessment_report(
    session_token: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Retrieves the finalized, reproducible assessment report snapshot.
    Enforces centralized clinical governance (withholds unapproved rules across all tiers and incomplete Tier 1).
    """
    return AssessmentProcessingService.get_assessment_report(
        db=db,
        session_token=session_token,
        current_user=current_user
    )
