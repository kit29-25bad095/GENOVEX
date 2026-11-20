import hmac
import hashlib
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Path, Header, status, Request, Response, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user_optional, User
from app.models.questionnaire import Assessment
from app.models.assessment_report import AssessmentReport
from app.schemas.questionnaire import (
    AssessmentStartRequest, AssessmentStartResponse, DomainQuestionsResponse,
    SaveDomainResponsesRequest, SaveDomainResponsesResponse, AssessmentReviewResponse,
    AssessmentSubmitResponse
)
from app.schemas.assessment_report import AssessmentReportResponse
from app.services.questionnaire_service import QuestionnaireService
from app.services.clinical_rule_engine import ClinicalRuleEngineService
from app.services.assessment_processing_service import AssessmentProcessingService

router = APIRouter(prefix="/questionnaire", tags=["Adaptive Questionnaire Engine"])

def generate_csrf_token(session_token: str) -> str:
    key = settings.SECRET_KEY.encode()
    msg = f"{session_token}:csrf".encode()
    return hmac.new(key, msg, hashlib.sha256).hexdigest()

def verify_csrf_token(session_token: str, csrf_token: str) -> bool:
    expected = generate_csrf_token(session_token)
    return hmac.compare_digest(expected, csrf_token)

def get_authorized_assessment(
    assessment_id: str = Path(..., min_length=10),
    request: Request = None,
    x_session_token: Optional[str] = Header(None, alias="X-Session-Token"),
    x_csrf_token: Optional[str] = Header(None, alias="X-CSRF-Token"),
    db: Session = Depends(get_db)
) -> Assessment:
    session_cookie = request.cookies.get("genovex_session") if request else None
    caller_token = session_cookie or x_session_token

    if not caller_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Assessment session credential required"
        )

    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )

    if not hmac.compare_digest(assessment.session_token, caller_token):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )

    # CSRF & Origin Guard on Mutating Requests
    if request and request.method in ("POST", "PUT", "DELETE", "PATCH"):
        # Anti-Bypass Guard: If genovex_session cookie is present, cookie auth mode is strictly enforced
        if session_cookie:
            origin = request.headers.get("origin")
            referer = request.headers.get("referer")
            allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000", "https://app.genovex.health"]
            if origin:
                if origin not in allowed_origins:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Untrusted origin")
            elif referer:
                if not any(referer.startswith(ao) for ao in allowed_origins):
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Untrusted origin")

            if not x_csrf_token or not verify_csrf_token(assessment.session_token, x_csrf_token):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or missing CSRF token")

    return assessment

@router.post("/assessments/start", response_model=AssessmentStartResponse)
def start_or_resume_assessment(
    req: AssessmentStartRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Initializes a new assessment or resumes an existing draft.
    Presents HttpOnly cookie and cryptographic CSRF token.
    """
    if req.session_token:
        cookie_token = request.cookies.get("genovex_session")
        header_token = request.headers.get("X-Session-Token")
        caller = cookie_token or header_token
        if caller and not hmac.compare_digest(caller, req.session_token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Assessment session credential required")

    start_res = QuestionnaireService.start_or_resume_assessment(
        db, user=None, session_token=req.session_token
    )
    csrf_token = generate_csrf_token(start_res.session_token)
    start_res.csrf_token = csrf_token

    response.set_cookie(
        key="genovex_session",
        value=start_res.session_token,
        httponly=True,
        samesite="lax",
        path="/",
        secure=False
    )
    response.set_cookie(
        key="genovex_csrf",
        value=csrf_token,
        httponly=False,
        samesite="lax",
        path="/",
        secure=False
    )
    return start_res

@router.get("/assessments/{assessment_id}/domain/{domain_index}", response_model=DomainQuestionsResponse)
def get_domain_questions(
    domain_index: int = Path(..., ge=0, le=10),
    assessment: Assessment = Depends(get_authorized_assessment),
    db: Session = Depends(get_db)
):
    """
    Retrieves questions for the specified clinical domain.
    Dynamically computes conditional follow-up question visibility based on prior answers.
    """
    return QuestionnaireService.get_domain_questions(db, assessment_id=assessment.id, domain_index=domain_index)

@router.post("/assessments/{assessment_id}/save-domain", response_model=SaveDomainResponsesResponse)
def save_domain_responses(
    data: SaveDomainResponsesRequest = ...,
    assessment: Assessment = Depends(get_authorized_assessment),
    db: Session = Depends(get_db)
):
    """
    Saves or auto-saves answers for the domain, performs downstream invalidation,
    and advances navigation progress.
    """
    return QuestionnaireService.save_domain_responses(db, assessment_id=assessment.id, data=data)

@router.get("/assessments/{assessment_id}/review", response_model=AssessmentReviewResponse)
def get_assessment_review(
    assessment: Assessment = Depends(get_authorized_assessment),
    db: Session = Depends(get_db)
):
    """
    Retrieves full pre-submission review breakdown across all 11 domains.
    Validates required questions, reconfirmation states, and identifies any unanswered items.
    """
    return QuestionnaireService.get_assessment_review(db, assessment_id=assessment.id)

@router.post("/assessments/{assessment_id}/submit", response_model=AssessmentSubmitResponse)
def submit_assessment(
    assessment: Assessment = Depends(get_authorized_assessment),
    db: Session = Depends(get_db)
):
    """
    Locks the assessment responses to the exact pinned questionnaire version.
    Triggers deterministic safety red-flag notification if acute symptoms were reported.
    """
    return QuestionnaireService.submit_assessment(db, assessment_id=assessment.id)

@router.post("/assessments/{assessment_id}/evaluate", response_model=AssessmentReportResponse)
def evaluate_assessment(
    assessment: Assessment = Depends(get_authorized_assessment),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Deterministically evaluates an assessment's responses against active clinical rules on sanitized ID route.
    Compiles an immutable AssessmentReport snapshot with evidence references and non-diagnostic explanations.
    Enforces centralized clinical governance (withholds unapproved rules and incomplete Tier 1).
    """
    return AssessmentProcessingService.process_assessment_results(
        db=db,
        assessment_id=assessment.id,
        session_token=assessment.session_token,
        current_user=current_user
    )

@router.get("/assessments/{assessment_id}/report", response_model=AssessmentReportResponse)
def get_assessment_report(
    assessment: Assessment = Depends(get_authorized_assessment),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Retrieves finalized, reproducible assessment report snapshot on sanitized ID route.
    Enforces centralized clinical governance (withholds unapproved rules and incomplete Tier 1).
    """
    return AssessmentProcessingService.get_assessment_report(
        db=db,
        assessment_id=assessment.id,
        session_token=assessment.session_token,
        current_user=current_user
    )
