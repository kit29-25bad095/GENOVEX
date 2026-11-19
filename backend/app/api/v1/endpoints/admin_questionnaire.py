from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import User, RoleEnum, require_roles
from app.schemas.questionnaire import (
    QuestionnaireVersionCreate, QuestionnaireVersionResponse,
    QuestionCreate, QuestionResponse
)
from app.services.questionnaire_service import QuestionnaireService
from app.models.questionnaire import Assessment

router = APIRouter(prefix="/admin/questionnaire", tags=["Admin - Questionnaire Management"])

@router.get("/versions", response_model=List[dict])
def list_versions(
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.CLINICIAN, RoleEnum.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """List all questionnaire versions and their publication status"""
    return QuestionnaireService.list_versions(db)

@router.post("/versions", response_model=QuestionnaireVersionResponse)
def create_version(
    data: QuestionnaireVersionCreate,
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Create a new draft questionnaire version"""
    return QuestionnaireService.create_version(db, data, user=current_user)

@router.post("/questions", response_model=QuestionResponse)
def add_question(
    data: QuestionCreate,
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Add a question with clinical rationale and conditional rules to a draft version"""
    return QuestionnaireService.add_question(db, data, user=current_user)

@router.post("/versions/{version_id}/publish", response_model=QuestionnaireVersionResponse)
def publish_version(
    version_id: int = Path(..., ge=1),
    notes: Optional[str] = Query(None, description="Clinical reviewer sign-off notes"),
    current_user: User = Depends(require_roles([RoleEnum.CLINICIAN, RoleEnum.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """
    Publish an approved questionnaire version for production use.
    Role-Guarded: Only Clinicians or SuperAdmins can approve and publish questionnaires.
    """
    return QuestionnaireService.publish_version(db, version_id=version_id, user=current_user, notes=notes)

@router.get("/assessments-overview")
def get_assessments_overview(
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.CLINICIAN, RoleEnum.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Retrieve metrics on in-progress, review-ready, and locked assessments"""
    total = db.query(Assessment).count()
    locked = db.query(Assessment).filter(Assessment.status == "LOCKED").count()
    in_progress = db.query(Assessment).filter(Assessment.status == "IN_PROGRESS").count()
    return {
        "total_assessments": total,
        "submitted_locked": locked,
        "in_progress": in_progress,
        "completion_rate": round((locked / max(1, total)) * 100, 1)
    }
