from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.clinical_rules import ClinicalOutcomeTier, ClinicalRuleStatus
from app.models.questionnaire import QuestionDomain
from app.schemas.clinical_rules import (
    ClinicalRuleCreate, ClinicalRuleUpdate, ClinicalRuleResponse,
    ClinicalRuleReviewAction, ClinicalRuleVersionResponse
)
from app.services.clinical_rule_management_service import ClinicalRuleManagementService
from app.core.security import get_current_user, User, RoleEnum

router = APIRouter(prefix="/admin/clinical-rules", tags=["Admin Clinical Rules Governance"])

@router.get("", response_model=List[ClinicalRuleResponse], summary="List clinical rules")
def list_clinical_rules(
    domain_code: Optional[QuestionDomain] = None,
    outcome_tier: Optional[ClinicalOutcomeTier] = None,
    status_filter: Optional[ClinicalRuleStatus] = Query(None, alias="status"),
    is_urgent: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all deterministic clinical rules with optional filtering by domain, tier, or status.
    """
    return ClinicalRuleManagementService.list_rules(
        db=db,
        domain_code=domain_code,
        outcome_tier=outcome_tier,
        status_filter=status_filter,
        is_urgent=is_urgent
    )

@router.post("", response_model=ClinicalRuleResponse, status_code=status.HTTP_201_CREATED, summary="Create draft clinical rule")
def create_clinical_rule(
    data: ClinicalRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a new draft clinical rule.
    """
    return ClinicalRuleManagementService.create_rule(db=db, data=data, current_user=current_user)

@router.get("/{rule_id}", response_model=ClinicalRuleResponse, summary="Get single clinical rule")
def get_clinical_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ClinicalRuleManagementService.get_rule_by_id(db=db, rule_id=rule_id)

@router.put("/{rule_id}", response_model=ClinicalRuleResponse, summary="Update draft clinical rule")
def update_clinical_rule(
    rule_id: int,
    data: ClinicalRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ClinicalRuleManagementService.update_rule(db=db, rule_id=rule_id, data=data, current_user=current_user)

@router.post("/{rule_id}/submit-review", response_model=ClinicalRuleResponse, summary="Submit rule for clinical review")
def submit_rule_for_review(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ClinicalRuleManagementService.submit_for_review(db=db, rule_id=rule_id, current_user=current_user)

@router.post("/{rule_id}/review", response_model=ClinicalRuleResponse, summary="Clinician review: approve or reject")
def clinical_review_rule(
    rule_id: int,
    action: ClinicalRuleReviewAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Strictly restricted to CLINICIAN or SUPER_ADMIN users.
    """
    return ClinicalRuleManagementService.clinical_review(db=db, rule_id=rule_id, action=action, current_user=current_user)

@router.post("/{rule_id}/publish", response_model=ClinicalRuleResponse, summary="Publish approved rule to live engine")
def publish_clinical_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Publishes an approved rule to production and creates an immutable version record.
    """
    return ClinicalRuleManagementService.publish_rule(db=db, rule_id=rule_id, current_user=current_user)

@router.get("/{rule_id}/versions", response_model=List[ClinicalRuleVersionResponse], summary="Get rule version history")
def get_rule_version_history(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ClinicalRuleManagementService.get_rule_versions(db=db, rule_id=rule_id)
