from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from fastapi import HTTPException, status

from app.models.questionnaire import (
    Assessment, AssessmentResponse, Question, QuestionnaireVersion, AssessmentStatus
)
from app.models.assessment_report import AssessmentReport
from app.models.clinical_rules import ClinicalRule
from app.core.security import User, RoleEnum, AuditLog
from app.services.ai_service import AIService
from app.schemas.clinician import (
    ReviewWorkflowStatus, ClinicianDashboardSummaryResponse,
    ClinicianAssessmentQueueItem, ClinicianAssessmentDetailResponse,
    ClinicianReviewStatusResponse, ClinicianNoteItem
)
from app.schemas.ai import ClinicianSummaryResponse


class ClinicianPortalService:
    """
    Centralized Clinician Portal Backend Service.
    Enforces strict Role-Based Access Control (CLINICIAN, ADMIN, SUPERADMIN),
    non-PII patient queue presentation, 5-state response inspection,
    review workflow lifecycle tracking via immutable AuditLog, and AI assistance.
    """

    @classmethod
    def _verify_clinician_access(cls, current_user: User) -> None:
        """Restricts portal access strictly to CLINICIAN, ADMIN, and SUPERADMIN roles."""
        if not current_user or current_user.role not in [RoleEnum.CLINICIAN, RoleEnum.ADMIN, RoleEnum.SUPERADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Clinician or Administrator privileges required."
            )

    @classmethod
    def _get_current_review_status(cls, db: Session, assessment_id: str) -> str:
        """Retrieves the latest review workflow status from the immutable audit trail."""
        latest_audit = db.query(AuditLog).filter(
            AuditLog.resource_type == "Assessment",
            AuditLog.resource_id == assessment_id,
            AuditLog.action == "CLINICIAN_REVIEW_WORKFLOW_UPDATE"
        ).order_by(desc(AuditLog.id)).first()

        if latest_audit and latest_audit.details:
            return latest_audit.details.get("new_status", ReviewWorkflowStatus.PENDING_REVIEW.value)
        return ReviewWorkflowStatus.PENDING_REVIEW.value

    @classmethod
    def get_clinician_dashboard(
        cls,
        db: Session,
        clinician_user: User
    ) -> ClinicianDashboardSummaryResponse:
        """
        Retrieves the clinician dashboard with queue metrics and accessible assessments.
        Excludes raw PII, using sanitized patient reference IDs (e.g. PT-XXXXXXXX).
        """
        cls._verify_clinician_access(clinician_user)

        # Retrieve submitted or locked assessments
        assessments = db.query(Assessment).filter(
            Assessment.status.in_([AssessmentStatus.LOCKED, AssessmentStatus.SUBMITTED])
        ).order_by(desc(Assessment.last_saved_at)).limit(50).all()

        queue_items: List[ClinicianAssessmentQueueItem] = []
        pending_count = 0
        in_review_count = 0
        completed_count = 0

        for a in assessments:
            report = db.query(AssessmentReport).filter(AssessmentReport.assessment_id == a.id).first()
            review_status = cls._get_current_review_status(db, a.id)

            if review_status == ReviewWorkflowStatus.PENDING_REVIEW.value:
                pending_count += 1
            elif review_status == ReviewWorkflowStatus.IN_REVIEW.value:
                in_review_count += 1
            elif review_status == ReviewWorkflowStatus.REVIEW_COMPLETED.value:
                completed_count += 1

            tier_val = getattr(report.outcome_tier, "value", str(report.outcome_tier)) if report else None
            is_urgent = report.is_urgent_red_flag if report else False

            queue_items.append(
                ClinicianAssessmentQueueItem(
                    assessment_id=a.id,
                    patient_reference=f"PT-{a.id[:8].upper()}",
                    status=a.status.value,
                    outcome_tier=tier_val,
                    is_urgent_red_flag=is_urgent,
                    review_workflow_status=review_status,
                    submitted_at=a.submitted_at.isoformat() if a.submitted_at else None,
                    last_activity_at=a.last_saved_at.isoformat() if a.last_saved_at else a.started_at.isoformat()
                )
            )

        return ClinicianDashboardSummaryResponse(
            clinician_id=clinician_user.id,
            clinician_name=clinician_user.full_name,
            credentials_summary=clinician_user.credentials_summary,
            assigned_assessments_count=len(queue_items),
            pending_review_count=pending_count,
            in_review_count=in_review_count,
            review_completed_count=completed_count,
            assessments_queue=queue_items
        )

    @classmethod
    def get_assessment_for_review(
        cls,
        db: Session,
        assessment_id: str,
        clinician_user: User
    ) -> ClinicianAssessmentDetailResponse:
        """
        Retrieves complete clinical audit details of an assessment:
        - 5-state response breakdown (answers, is_unsure, is_prefer_not_to_say, conditional_pathway_active, needs_reconfirmation)
        - Deterministic report snapshot
        - Review workflow history
        """
        cls._verify_clinician_access(clinician_user)

        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment record not found")

        # Log clinician inspection audit
        try:
            audit = AuditLog(
                user_id=clinician_user.id,
                action="CLINICIAN_ASSESSMENT_INSPECT",
                resource_type="Assessment",
                resource_id=assessment.id,
                details={
                    "clinician_id": clinician_user.id,
                    "clinician_name": clinician_user.full_name,
                    "status": assessment.status.value
                },
                timestamp=datetime.now(timezone.utc)
            )
            db.add(audit)
            db.commit()
        except Exception:
            db.rollback()

        # Build response breakdown with five-state distinctions
        responses_list = []
        for r in assessment.responses:
            q = r.question
            responses_list.append({
                "question_key": r.question_key,
                "domain_code": q.domain_code.value if q else "UNKNOWN",
                "prompt_en": q.text_en if q else r.question_key,
                "prompt_ar": q.text_ar if q else r.question_key,
                "answer_value": r.answer_value,
                "is_unsure": r.is_unsure,
                "is_prefer_not_to_say": r.is_prefer_not_to_say,
                "conditional_pathway_active": r.conditional_pathway_active,
                "needs_reconfirmation": getattr(r, "needs_reconfirmation", False),
                "is_urgent_red_flag": q.is_urgent_red_flag if q else False
            })

        # Compiled report snapshot
        report = db.query(AssessmentReport).filter(AssessmentReport.assessment_id == assessment.id).first()
        report_dict = None
        is_incomplete = False
        if report:
            is_incomplete = "INCOMPLETE EVALUATION" in (report.outcome_title_en or "").upper()
            report_dict = {
                "report_reference": report.report_reference,
                "outcome_tier": getattr(report.outcome_tier, "value", str(report.outcome_tier)),
                "outcome_title_en": report.outcome_title_en,
                "outcome_title_ar": report.outcome_title_ar,
                "outcome_description_en": report.outcome_description_en,
                "outcome_description_ar": report.outcome_description_ar,
                "is_urgent_red_flag": report.is_urgent_red_flag,
                "urgent_emergency_guidance_en": report.urgent_emergency_guidance_en,
                "recommended_specialties": report.recommended_specialties,
                "identified_risk_factors": report.identified_risk_factors_json,
                "triggered_rules": report.triggered_rules_snapshot_json,
                "evidence_citations": report.evidence_citations_json,
                "generated_at": report.generated_at.isoformat() if report.generated_at else None
            }

        # Check for unapproved rules in system
        unapproved_rules = db.query(ClinicalRule).filter(
            (ClinicalRule.clinical_reviewer_id.is_(None)) | (ClinicalRule.approved_at.is_(None))
        ).count()

        # Review workflow history from audit trail
        history_records = db.query(AuditLog).filter(
            AuditLog.resource_type == "Assessment",
            AuditLog.resource_id == assessment.id,
            AuditLog.action.in_(["CLINICIAN_REVIEW_WORKFLOW_UPDATE", "CLINICIAN_INTERNAL_NOTE"])
        ).order_by(desc(AuditLog.id)).all()

        history_list = []
        for h in history_records:
            history_list.append({
                "action": h.action,
                "user_id": h.user_id,
                "details": h.details,
                "timestamp": h.timestamp.isoformat() if h.timestamp else ""
            })

        current_status = cls._get_current_review_status(db, assessment.id)

        return ClinicianAssessmentDetailResponse(
            assessment_id=assessment.id,
            patient_reference=f"PT-{assessment.id[:8].upper()}",
            status=assessment.status.value,
            questionnaire_version_tag=assessment.questionnaire_version.version_tag if assessment.questionnaire_version else "v1.0.0",
            current_review_status=current_status,
            submitted_at=assessment.submitted_at.isoformat() if assessment.submitted_at else None,
            responses=responses_list,
            deterministic_report=report_dict,
            review_history=history_list,
            has_unapproved_rules=unapproved_rules > 0,
            is_evaluation_incomplete=is_incomplete
        )

    @classmethod
    def update_review_workflow_status(
        cls,
        db: Session,
        assessment_id: str,
        new_status: ReviewWorkflowStatus,
        notes: Optional[str],
        clinician_user: User
    ) -> ClinicianReviewStatusResponse:
        """
        Updates the assessment review workflow status.
        Persisted via immutable AuditLog without altering historical assessment/report records.
        """
        cls._verify_clinician_access(clinician_user)

        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

        prev_status = cls._get_current_review_status(db, assessment.id)

        try:
            audit = AuditLog(
                user_id=clinician_user.id,
                user_email=clinician_user.email,
                user_role=clinician_user.role.value,
                action="CLINICIAN_REVIEW_WORKFLOW_UPDATE",
                resource_type="Assessment",
                resource_id=assessment.id,
                details={
                    "previous_status": prev_status,
                    "new_status": new_status.value,
                    "notes": notes,
                    "clinician_id": clinician_user.id,
                    "clinician_name": clinician_user.full_name
                },
                timestamp=datetime.now(timezone.utc)
            )
            db.add(audit)
            db.commit()
            db.refresh(audit)

            return ClinicianReviewStatusResponse(
                assessment_id=assessment.id,
                previous_status=prev_status,
                current_status=new_status.value,
                updated_by_clinician_id=clinician_user.id,
                updated_at=audit.timestamp.isoformat(),
                audit_log_id=audit.id
            )
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to record review status transition: {str(e)}"
            )

    @classmethod
    def add_clinician_note(
        cls,
        db: Session,
        assessment_id: str,
        note_text: str,
        clinician_user: User
    ) -> ClinicianNoteItem:
        """
        Records a confidential clinician internal note in the immutable audit trail.
        Never exposed to patient-facing routes.
        """
        cls._verify_clinician_access(clinician_user)

        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

        try:
            audit = AuditLog(
                user_id=clinician_user.id,
                user_email=clinician_user.email,
                user_role=clinician_user.role.value,
                action="CLINICIAN_INTERNAL_NOTE",
                resource_type="Assessment",
                resource_id=assessment.id,
                details={
                    "note_text": note_text,
                    "author_name": clinician_user.full_name,
                    "author_role": clinician_user.role.value
                },
                timestamp=datetime.now(timezone.utc)
            )
            db.add(audit)
            db.commit()
            db.refresh(audit)

            return ClinicianNoteItem(
                note_id=audit.id,
                author_name=clinician_user.full_name,
                author_role=clinician_user.role.value,
                note_text=note_text,
                created_at=audit.timestamp.isoformat()
            )
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to record clinician note: {str(e)}"
            )

    @classmethod
    def get_clinician_notes(
        cls,
        db: Session,
        assessment_id: str,
        clinician_user: User
    ) -> List[ClinicianNoteItem]:
        """Retrieves all clinician internal notes for this assessment."""
        cls._verify_clinician_access(clinician_user)

        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

        notes_audit = db.query(AuditLog).filter(
            AuditLog.resource_type == "Assessment",
            AuditLog.resource_id == assessment.id,
            AuditLog.action == "CLINICIAN_INTERNAL_NOTE"
        ).order_by(desc(AuditLog.id)).all()

        items = []
        for n in notes_audit:
            details = n.details or {}
            items.append(
                ClinicianNoteItem(
                    note_id=n.id,
                    author_name=details.get("author_name", "Clinician"),
                    author_role=details.get("author_role", "CLINICIAN"),
                    note_text=details.get("note_text", ""),
                    created_at=n.timestamp.isoformat() if n.timestamp else ""
                )
            )
        return items

    @classmethod
    async def get_ai_assessment_summary(
        cls,
        db: Session,
        assessment_id: str,
        focus_areas: Optional[List[str]],
        clinician_user: User
    ) -> ClinicianSummaryResponse:
        """
        Generates an AI-synthesized clinical summary for attending clinician review.
        """
        cls._verify_clinician_access(clinician_user)

        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

        return await AIService.generate_clinician_assessment_summary(
            db=db,
            assessment=assessment,
            clinician_user=clinician_user,
            focus_areas=focus_areas
        )
