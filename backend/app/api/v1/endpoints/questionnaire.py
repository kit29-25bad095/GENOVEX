from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Path, Header, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, User
from app.schemas.questionnaire import (
    AssessmentStartRequest, AssessmentStartResponse, DomainQuestionsResponse,
    SaveDomainResponsesRequest, SaveDomainResponsesResponse, AssessmentReviewResponse,
    AssessmentSubmitResponse
)
from app.services.questionnaire_service import QuestionnaireService

router = APIRouter(prefix="/questionnaire", tags=["Adaptive Questionnaire Engine"])

@router.post("/assessments/start", response_model=AssessmentStartResponse)
def start_or_resume_assessment(
    req: AssessmentStartRequest,
    db: Session = Depends(get_db)
):
    """
    Initializes a new assessment or resumes an existing draft.
    Critically: Pinned to the active published questionnaire version.
    """
    return QuestionnaireService.start_or_resume_assessment(
        db, user=None, session_token=req.session_token
    )

@router.get("/assessments/{assessment_id}/domain/{domain_index}", response_model=DomainQuestionsResponse)
def get_domain_questions(
    assessment_id: str = Path(..., min_length=10),
    domain_index: int = Path(..., ge=0, le=10),
    db: Session = Depends(get_db)
):
    """
    Retrieves questions for the specified clinical domain.
    Dynamically computes conditional follow-up question visibility based on prior answers.
    """
    return QuestionnaireService.get_domain_questions(db, assessment_id=assessment_id, domain_index=domain_index)

@router.post("/assessments/{assessment_id}/save-domain", response_model=SaveDomainResponsesResponse)
def save_domain_responses(
    assessment_id: str = Path(..., min_length=10),
    data: SaveDomainResponsesRequest = ...,
    db: Session = Depends(get_db)
):
    """
    Saves or auto-saves answers for the domain, checks deterministic red flags,
    and advances navigation progress.
    """
    return QuestionnaireService.save_domain_responses(db, assessment_id=assessment_id, data=data)

@router.get("/assessments/{assessment_id}/review", response_model=AssessmentReviewResponse)
def get_assessment_review(
    assessment_id: str = Path(..., min_length=10),
    db: Session = Depends(get_db)
):
    """
    Retrieves full pre-submission review breakdown across all 11 domains.
    Validates required questions and identifies any unanswered items.
    """
    return QuestionnaireService.get_assessment_review(db, assessment_id=assessment_id)

@router.post("/assessments/{assessment_id}/submit", response_model=AssessmentSubmitResponse)
def submit_assessment(
    assessment_id: str = Path(..., min_length=10),
    db: Session = Depends(get_db)
):
    """
    Locks the assessment responses to the exact pinned questionnaire version.
    Triggers deterministic safety red-flag notification if acute symptoms were reported.
    """
    return QuestionnaireService.submit_assessment(db, assessment_id=assessment_id)
