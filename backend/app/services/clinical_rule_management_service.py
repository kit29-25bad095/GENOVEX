import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.clinical_rules import (
    ClinicalRule, ClinicalOutcomeTier, ClinicalRuleStatus, ClinicalRuleVersionRecord
)
from app.models.questionnaire import QuestionDomain
from app.schemas.clinical_rules import ClinicalRuleCreate, ClinicalRuleUpdate, ClinicalRuleReviewAction
from app.core.security import User, RoleEnum

class ClinicalRuleManagementService:
    """
    Service for administrative and clinical governance of deterministic clinical rules.
    Enforces RBAC: only authorized clinical reviewers can approve and publish clinical rules.
    """

    @staticmethod
    def list_rules(
        db: Session,
        domain_code: Optional[QuestionDomain] = None,
        outcome_tier: Optional[ClinicalOutcomeTier] = None,
        status_filter: Optional[ClinicalRuleStatus] = None,
        is_urgent: Optional[bool] = None
    ) -> List[ClinicalRule]:
        q = db.query(ClinicalRule)
        if domain_code:
            q = q.filter(ClinicalRule.domain_code == domain_code)
        if outcome_tier:
            q = q.filter(ClinicalRule.outcome_tier == outcome_tier)
        if status_filter:
            q = q.filter(ClinicalRule.status == status_filter)
        if is_urgent is not None:
            q = q.filter(ClinicalRule.is_urgent_red_flag == is_urgent)
        return q.order_by(ClinicalRule.priority_rank.asc()).all()

    @staticmethod
    def get_rule_by_id(db: Session, rule_id: int) -> ClinicalRule:
        rule = db.query(ClinicalRule).filter(ClinicalRule.id == rule_id).first()
        if not rule:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinical rule not found")
        return rule

    @classmethod
    def create_rule(cls, db: Session, data: ClinicalRuleCreate, current_user: User) -> ClinicalRule:
        # Check rule code uniqueness
        existing = db.query(ClinicalRule).filter(ClinicalRule.rule_code == data.rule_code).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Rule code '{data.rule_code}' already exists")

        rule = ClinicalRule(
            rule_code=data.rule_code,
            title_en=data.title_en,
            title_ar=data.title_ar,
            target_condition_slug=data.target_condition_slug,
            domain_code=data.domain_code,
            relevant_question_keys=data.relevant_question_keys,
            outcome_tier=data.outcome_tier,
            is_urgent_red_flag=data.is_urgent_red_flag,
            priority_rank=data.priority_rank,
            recommended_specialty=data.recommended_specialty,
            trigger_criteria=data.trigger_criteria,
            missing_response_handling=data.missing_response_handling,
            clinical_rationale_en=data.clinical_rationale_en,
            clinical_rationale_ar=data.clinical_rationale_ar,
            evidence_references=data.evidence_references,
            evidence_classification=data.evidence_classification,
            rule_version="1.0.0",
            status=ClinicalRuleStatus.DRAFT,
            created_by_user_id=current_user.id
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)
        return rule

    @classmethod
    def update_rule(cls, db: Session, rule_id: int, data: ClinicalRuleUpdate, current_user: User) -> ClinicalRule:
        rule = cls.get_rule_by_id(db, rule_id)
        if rule.status == ClinicalRuleStatus.PUBLISHED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Published clinical rules cannot be silently updated. Create a new draft revision or retire the rule."
            )

        update_dict = data.model_dump(exclude_unset=True)
        for key, val in update_dict.items():
            setattr(rule, key, val)

        # Reset approval if edited
        if rule.status == ClinicalRuleStatus.APPROVED:
            rule.status = ClinicalRuleStatus.DRAFT

        db.commit()
        db.refresh(rule)
        return rule

    @classmethod
    def submit_for_review(cls, db: Session, rule_id: int, current_user: User) -> ClinicalRule:
        rule = cls.get_rule_by_id(db, rule_id)
        if rule.status != ClinicalRuleStatus.DRAFT:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only DRAFT rules can be submitted for review")
        
        rule.status = ClinicalRuleStatus.SUBMITTED_FOR_REVIEW
        db.commit()
        db.refresh(rule)
        return rule

    @classmethod
    def clinical_review(cls, db: Session, rule_id: int, action: ClinicalRuleReviewAction, current_user: User) -> ClinicalRule:
        # Strict RBAC: only CLINICIAN or SUPERADMIN
        if current_user.role not in [RoleEnum.CLINICIAN, RoleEnum.SUPERADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Clinical rules can only be approved by authorized CLINICIANS or SUPERADMINS."
            )

        rule = cls.get_rule_by_id(db, rule_id)
        if rule.status != ClinicalRuleStatus.SUBMITTED_FOR_REVIEW:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rule must be in SUBMITTED_FOR_REVIEW status")

        rule.clinical_reviewer_id = current_user.id
        rule.clinical_reviewer_notes = action.reviewer_notes

        if action.action.upper() == "APPROVE":
            rule.status = ClinicalRuleStatus.APPROVED
            rule.approved_at = datetime.now(timezone.utc)
        elif action.action.upper() == "REJECT":
            rule.status = ClinicalRuleStatus.DRAFT
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Action must be APPROVE or REJECT")

        db.commit()
        db.refresh(rule)
        return rule

    @classmethod
    def publish_rule(cls, db: Session, rule_id: int, current_user: User) -> ClinicalRule:
        if current_user.role not in [RoleEnum.CLINICIAN, RoleEnum.SUPERADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Publishing clinical rules requires clinical reviewer authorization."
            )

        rule = cls.get_rule_by_id(db, rule_id)
        if rule.status != ClinicalRuleStatus.APPROVED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only APPROVED rules can be published")

        rule.status = ClinicalRuleStatus.PUBLISHED
        rule.published_at = datetime.now(timezone.utc)

        # Create immutable historical version snapshot
        snapshot = {
            "rule_code": rule.rule_code,
            "title_en": rule.title_en,
            "title_ar": rule.title_ar,
            "domain_code": rule.domain_code.value,
            "outcome_tier": rule.outcome_tier.value,
            "is_urgent_red_flag": rule.is_urgent_red_flag,
            "priority_rank": rule.priority_rank,
            "recommended_specialty": rule.recommended_specialty,
            "trigger_criteria": rule.trigger_criteria,
            "clinical_rationale_en": rule.clinical_rationale_en,
            "clinical_rationale_ar": rule.clinical_rationale_ar,
            "evidence_references": rule.evidence_references,
            "evidence_classification": rule.evidence_classification
        }

        version_record = ClinicalRuleVersionRecord(
            rule_id=rule.id,
            version_tag=rule.rule_version,
            rule_code=rule.rule_code,
            title_en=rule.title_en,
            title_ar=rule.title_ar,
            outcome_tier=rule.outcome_tier,
            is_urgent_red_flag=rule.is_urgent_red_flag,
            trigger_criteria=rule.trigger_criteria,
            evidence_references=rule.evidence_references,
            snapshot_json=snapshot,
            created_by_user_id=current_user.id
        )
        db.add(version_record)

        db.commit()
        db.refresh(rule)
        return rule

    @classmethod
    def get_rule_versions(cls, db: Session, rule_id: int) -> List[ClinicalRuleVersionRecord]:
        return db.query(ClinicalRuleVersionRecord).filter(
            ClinicalRuleVersionRecord.rule_id == rule_id
        ).order_by(ClinicalRuleVersionRecord.created_at.desc()).all()
