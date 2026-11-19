from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.questionnaire import Assessment, AssessmentStatus
from app.schemas.assessment_report import AssessmentReportResponse
from app.services.clinical_rule_engine import ClinicalRuleEngineService
from app.core.security import get_current_user_optional, User

router = APIRouter(prefix="/assessment", tags=["Assessment Evaluation & Reports"])

@router.post("/{session_token}/evaluate", response_model=AssessmentReportResponse, summary="Evaluate assessment & compile report")
def evaluate_assessment(
    session_token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Deterministically evaluates an assessment's responses against active clinical rules.
    Compiles an immutable AssessmentReport snapshot with evidence references and non-diagnostic explanations.
    """
    assessment = db.query(Assessment).filter(Assessment.session_token == session_token).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment session not found")

    user_id = current_user.id if current_user else assessment.user_id

    report = ClinicalRuleEngineService.compile_assessment_report(
        db=db,
        assessment_id=assessment.id,
        session_token=session_token,
        user_id=user_id
    )
    return report

@router.get("/{session_token}/report", response_model=AssessmentReportResponse, summary="Get compiled assessment report")
def get_assessment_report(
    session_token: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves the finalized, reproducible assessment report snapshot.
    """
    return ClinicalRuleEngineService.get_report_by_session(db=db, session_token=session_token)
