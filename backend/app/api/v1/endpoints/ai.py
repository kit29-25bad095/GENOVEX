from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_optional, User
from app.services.ai_service import AIService
from app.schemas.ai import (
    HealthEducationRequest, HealthEducationResponse,
    TerminologyExplanationRequest, TerminologyExplanationResponse,
    ResultExplanationRequest, ResultExplanationResponse,
    PreparationQuestionsRequest, PreparationQuestionsResponse
)

router = APIRouter(prefix="/ai", tags=["AI Educational & Decision Support Integration"])


@router.post("/explain-topic", response_model=HealthEducationResponse, summary="Explain male reproductive health & lifestyle topic")
async def explain_health_topic(
    payload: HealthEducationRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Plain-language educational explanation of male reproductive health concepts and guidelines.
    Enforces prompt injection sanitization, rate limiting, and output safety invariants.
    """
    caller_id = current_user.email if current_user else (request.client.host if request.client else "anonymous")
    return await AIService.explain_health_topic(
        db=db,
        topic=payload.topic,
        context=payload.context,
        language=payload.language,
        current_user=current_user,
        caller_id=caller_id
    )


@router.post("/explain-terminology", response_model=TerminologyExplanationResponse, summary="Explain clinical reproductive terminology")
async def explain_terminology(
    payload: TerminologyExplanationRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Plain-language explanation of medical terminology without diagnostic assertions.
    """
    caller_id = current_user.email if current_user else (request.client.host if request.client else "anonymous")
    return await AIService.explain_terminology(
        db=db,
        term=payload.term,
        language=payload.language,
        current_user=current_user,
        caller_id=caller_id
    )


@router.post("/explain-result", response_model=ResultExplanationResponse, summary="Explain deterministic assessment results in plain language")
async def explain_assessment_result(
    payload: ResultExplanationRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Consumes finalized deterministic report snapshot as read-only input.
    Enforces centralized clinical governance (withholds unapproved rules and incomplete Tier 1).
    Preserves exact outcome tier and non-diagnostic legal notices.
    """
    return await AIService.explain_assessment_result(
        db=db,
        report_reference=payload.report_reference,
        session_token=payload.session_token,
        language=payload.language,
        current_user=current_user
    )


@router.post("/preparation-questions", response_model=PreparationQuestionsResponse, summary="Generate preparation questions for doctor consultation")
async def generate_preparation_questions(
    payload: PreparationQuestionsRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Generates tailored questions for the patient to ask their attending urologist or andrologist.
    """
    return await AIService.generate_preparation_questions(
        db=db,
        report_reference=payload.report_reference,
        session_token=payload.session_token,
        language=payload.language,
        current_user=current_user
    )
