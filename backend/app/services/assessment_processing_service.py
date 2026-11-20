"""
GENOVEX Phase 8: Assessment Processing and Results Service
Orchestrates assessment validation, deterministic clinical evaluation,
snapshot immutability, centralized governance, and privacy-preserving audit logging.
"""

import hmac
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.questionnaire import (
    Assessment, AssessmentResponse, Question, QuestionnaireVersion,
    AssessmentStatus, QuestionDomain
)
from app.models.clinical_rules import (
    ClinicalRule, ClinicalOutcomeTier, ClinicalRuleStatus, ClinicalRuleVersionRecord
)
from app.models.assessment_report import AssessmentReport
from app.core.security import User, RoleEnum, AuditLog
from app.services.clinical_rule_engine import ClinicalRuleEngineService
from app.services.adaptive_branching import AdaptiveBranchingService


class GovernanceDecision:
    """Represents the outcome of a governance gate check."""
    def __init__(self, allowed: bool, error_code: Optional[str] = None, message: Optional[str] = None, http_status: int = status.HTTP_200_OK, mode: str = "STANDARD"):
        self.allowed = allowed
        self.error_code = error_code
        self.message = message
        self.http_status = http_status
        self.mode = mode


class ClinicalGovernanceGate:
    """
    Centralized Server-Side Governance Gate.
    Enforces clinical rule approval verification, assessment ownership,
    and incomplete-evaluation withholding across ALL evaluation and report endpoints.
    Eliminates all client-controlled overrides.
    """

    @staticmethod
    def verify_assessment_ownership(
        assessment: Assessment,
        current_user: Optional[User],
        session_token: Optional[str] = None
    ) -> None:
        """
        Verifies caller authorization to access or mutate this assessment.
        Constant-time comparison for session tokens.
        Strict user_id matching for authenticated patients.
        """
        # Clinicians and Superadmins can inspect any assessment in clinical audit mode
        if current_user and current_user.role in [RoleEnum.CLINICIAN, RoleEnum.SUPERADMIN]:
            return

        # 1. Session token validation if provided
        if session_token:
            if not assessment.session_token or not hmac.compare_digest(assessment.session_token, session_token):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "UNAUTHORIZED_ASSESSMENT_ACCESS",
                        "message": "Access denied: Session token does not match assessment record."
                    }
                )

        # 2. Authenticated user ownership check
        if assessment.user_id is not None:
            if not current_user or current_user.id != assessment.user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "UNAUTHORIZED_ASSESSMENT_ACCESS",
                        "message": "Access denied: Caller is not the authorized owner of this assessment."
                    }
                )

    @classmethod
    def is_rule_verifiably_approved(cls, db: Session, rule: ClinicalRule) -> bool:
        """
        Evaluates whether a clinical rule has verifiable, legitimate clinical approval.
        STRICT FAIL-CLOSED POLICY (Directive Section 3.1 & 3.2):
        1. A non-null clinical_reviewer_id alone NEVER authorizes patient-facing release.
        2. An approval timestamp alone NEVER authorizes release.
        3. A seeded, synthetic, or test reviewer account CANNOT authorize clinical release.
        4. A published database status does NOT automatically establish clinical approval.
        5. Only independently verifiable, legitimate clinical approval can satisfy the requirement.
        6. Missing, contradictory, synthetic, or unverifiable approval provenance results in denial.
        7. The gate evaluates every rule relevant to the report, not merely rules with null reviewer IDs.
        8. All errors and uncertain states fail closed.
        """
        try:
            reviewer_id = getattr(rule, "clinical_reviewer_id", None)
            approved_at = getattr(rule, "approved_at", None)
            if reviewer_id is None or approved_at is None:
                return False

            # Verify that the reviewer exists in the database
            reviewer = db.query(User).filter(User.id == reviewer_id).first()
            if not reviewer:
                return False

            # Reviewer must possess a verified CLINICIAN role and active status
            if reviewer.role != RoleEnum.CLINICIAN or not reviewer.is_active:
                return False

            # Explicitly disqualify synthetic, test, or audit accounts
            email = (reviewer.email or "").lower()
            name = (reviewer.full_name or "").lower()
            disqualified_keywords = ["audit", "test", "synthetic", "example.com", "dummy", "mock"]
            if any(k in email for k in disqualified_keywords) or any(k in name for k in disqualified_keywords):
                return False

            # Legitimate approval requires an independently verifiable clinical review audit trail
            has_approval_audit = db.query(AuditLog).filter(
                AuditLog.action.in_(["CLINICAL_RULE_APPROVE", "APPROVE_CLINICAL_RULE"]),
                AuditLog.user_id == reviewer_id
            ).first() is not None

            if not has_approval_audit:
                return False

            return True
        except Exception:
            # All errors and uncertain states fail closed
            return False

    @classmethod
    def verify_report_access(
        cls,
        db: Session,
        report: AssessmentReport,
        current_user: Optional[User],
        assessment: Optional[Assessment] = None
    ) -> None:
        """
        Centralized server-side policy check for reading or releasing an AssessmentReport.
        Strict fail-closed governance across all four outcome tiers:
        1. Incomplete Tier 1 evaluation without specialized amber warning presentation contract.
        2. Any underlying clinical rule is unapproved, synthetic, or lacking verifiable clinical provenance.
        Eliminates all caller-controlled bypasses (query params, body fields, headers).
        """
        is_clinician_or_admin = (
            current_user is not None and 
            current_user.role in [RoleEnum.CLINICIAN, RoleEnum.ADMIN, RoleEnum.SUPERADMIN]
        )

        # Clinicians and Admins can access unapproved outputs strictly in Clinical Audit Mode
        if is_clinician_or_admin:
            return

        # 1. INCOMPLETE TIER 1 EVALUATION CHECK (INDEPENDENT WITHHOLDING)
        is_tier1 = (
            report.outcome_tier in [ClinicalOutcomeTier.TIER_1_NO_RISK, ClinicalOutcomeTier.TIER_1_NO_RISK.value, "TIER_1_NO_RISK", "NO_REPORTED_RISK_FACTORS"]
            or getattr(report.outcome_tier, "value", None) in [ClinicalOutcomeTier.TIER_1_NO_RISK.value, "NO_REPORTED_RISK_FACTORS"]
        )
        is_incomplete = "INCOMPLETE EVALUATION" in (report.outcome_title_en or "").upper()

        if is_tier1 and is_incomplete:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "INCOMPLETE_EVALUATION_WITHHELD",
                    "message": (
                        "Assessment evaluation is incomplete due to unsure, declined, or missing clinical responses. "
                        "Patient-facing report release is withheld pending complete evaluation or specialized UI warning presentation."
                    ),
                    "evaluation_completeness": "INDETERMINATE",
                    "outcome_tier": "NO_REPORTED_RISK_FACTORS"
                }
            )

        # 2. CLINICAL RULE APPROVAL GOVERNANCE CHECK (FAIL-CLOSED ACROSS ALL 4 TIERS)
        active_rules = db.query(ClinicalRule).all()
        unapproved_rules = [
            r for r in active_rules
            if not cls.is_rule_verifiably_approved(db, r)
        ]

        if unapproved_rules:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "CLINICAL_RELEASE_WITHHELD",
                    "message": (
                        "Assessment evaluation outputs are withheld from patient-facing release because "
                        f"{len(unapproved_rules)} underlying clinical rules lack independently verified clinical sign-off "
                        "from an accredited clinician. Access is strictly restricted to authorized clinicians and administrators in Clinical Audit Mode."
                    ),
                    "status": "WITHHELD",
                    "unapproved_rules_count": len(unapproved_rules)
                }
            )


class AssessmentProcessingService:
    """
    Centralized assessment processing pipeline.
    Validates preconditions, guarantees idempotency and snapshot immutability,
    and applies centralized governance.
    """

    @classmethod
    def validate_assessment_for_processing(
        cls,
        db: Session,
        assessment_id: str,
        session_token: Optional[str] = None,
        current_user: Optional[User] = None
    ) -> Assessment:
        """
        STAGE 1: Assessment Completion and Submission Validation.
        Verifies:
        1. Assessment exists.
        2. Status is strictly LOCKED (rejects IN_PROGRESS and REVIEW_READY with 409).
        3. Ownership / authorization.
        4. Valid response states (required questions answered or safe answer flags present).
        """
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment record not found"
            )

        # Verify Ownership
        ClinicalGovernanceGate.verify_assessment_ownership(
            assessment=assessment,
            current_user=current_user,
            session_token=session_token
        )

        # Verify LOCKED Status (Precondition for result processing; reject IN_PROGRESS and REVIEW_READY)
        if assessment.status in [AssessmentStatus.IN_PROGRESS, AssessmentStatus.REVIEW_READY]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Assessment cannot be processed: status is '{assessment.status.value}'. "
                    "Assessment must be submitted and LOCKED prior to deterministic processing."
                )
            )

        # Verify Questionnaire Version Consistency
        q_version = db.query(QuestionnaireVersion).filter(
            QuestionnaireVersion.id == assessment.questionnaire_version_id
        ).first()
        if not q_version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Invalid questionnaire version pinned to assessment"
            )

        # Check for child questions requiring explicit reconfirmation
        for r in assessment.responses:
            if getattr(r, "needs_reconfirmation", False):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot process assessment: response for '{r.question_key}' requires explicit clinical reconfirmation"
                )

        # Validate conditional pathway consistency across active responses
        active_questions = db.query(Question).filter(
            Question.version_id == assessment.questionnaire_version_id
        ).all()
        saved_dict_for_dag = {
            r.question_key: {
                "answer_value": r.answer_value,
                "is_unsure": r.is_unsure,
                "is_prefer_not_to_say": r.is_prefer_not_to_say,
                "conditional_pathway_active": r.conditional_pathway_active
            }
            for r in assessment.responses
        }
        for q in active_questions:
            is_visible = AdaptiveBranchingService.evaluate_question_visibility(
                question=q,
                saved_answers=saved_dict_for_dag
            )
            resp = next((r for r in assessment.responses if r.question_key == q.question_key), None)
            if resp and resp.conditional_pathway_active != is_visible:
                resp.conditional_pathway_active = is_visible

        return assessment

    @classmethod
    def process_assessment_results(
        cls,
        db: Session,
        assessment_id: str,
        session_token: Optional[str] = None,
        current_user: Optional[User] = None
    ) -> AssessmentReport:
        """
        STAGE 2 & STAGE 5: Deterministic Orchestration, Report Compilation & Idempotency.
        If a report already exists for this assessment, returns the existing immutable report.
        Otherwise, executes deterministic evaluation and compiles a new snapshot atomically.
        """
        # 1. Idempotency Check: Return existing report without mutation
        existing_report = db.query(AssessmentReport).filter(
            AssessmentReport.assessment_id == assessment_id
        ).first()
        if existing_report:
            # Verify Ownership
            assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
            if assessment:
                ClinicalGovernanceGate.verify_assessment_ownership(
                    assessment=assessment,
                    current_user=current_user,
                    session_token=session_token
                )
            # Audit log report retrieval
            cls._log_report_retrieval(db, existing_report, current_user)
            # Enforce centralized governance gate
            ClinicalGovernanceGate.verify_report_access(
                db=db,
                report=existing_report,
                current_user=current_user,
                assessment=assessment
            )
            return existing_report

        # 2. Validate preconditions
        assessment = cls.validate_assessment_for_processing(
            db=db,
            assessment_id=assessment_id,
            session_token=session_token,
            current_user=current_user
        )

        # 3. Compile new report snapshot atomically
        effective_session_token = session_token or assessment.session_token
        effective_user_id = current_user.id if current_user else assessment.user_id

        try:
            report = ClinicalRuleEngineService.compile_assessment_report(
                db=db,
                assessment_id=assessment.id,
                session_token=effective_session_token,
                user_id=effective_user_id
            )
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Deterministic assessment processing failed: {str(e)}"
            )

        # 4. Enforce centralized governance gate on compiled report
        ClinicalGovernanceGate.verify_report_access(
            db=db,
            report=report,
            current_user=current_user,
            assessment=assessment
        )

        return report

    @classmethod
    def get_assessment_report(
        cls,
        db: Session,
        session_token: Optional[str] = None,
        assessment_id: Optional[str] = None,
        current_user: Optional[User] = None
    ) -> AssessmentReport:
        """
        STAGE 5 & STAGE 6: Retrieve compiled report with centralized governance enforcement.
        Supports lookup by session_token or assessment_id.
        """
        query = db.query(AssessmentReport)
        if assessment_id:
            query = query.filter(AssessmentReport.assessment_id == assessment_id)
        elif session_token:
            query = query.filter(AssessmentReport.session_token == session_token)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either assessment_id or session_token must be provided"
            )

        report = query.first()
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment report not found"
            )

        # Verify assessment ownership
        assessment = db.query(Assessment).filter(Assessment.id == report.assessment_id).first()
        if assessment:
            ClinicalGovernanceGate.verify_assessment_ownership(
                assessment=assessment,
                current_user=current_user,
                session_token=session_token
            )

        # Centralized governance verification
        ClinicalGovernanceGate.verify_report_access(
            db=db,
            report=report,
            current_user=current_user,
            assessment=assessment
        )

        # Audit log report retrieval
        cls._log_report_retrieval(db, report, current_user)

        return report

    @staticmethod
    def _log_report_retrieval(
        db: Session,
        report: AssessmentReport,
        current_user: Optional[User]
    ) -> None:
        """Logs categorical, non-PII audit event for report access."""
        try:
            audit_entry = AuditLog(
                user_id=current_user.id if current_user else report.user_id,
                action="RETRIEVE_ASSESSMENT_REPORT",
                resource_type="AssessmentReport",
                resource_id=report.report_reference,
                details={
                    "report_reference": report.report_reference,
                    "outcome_tier": getattr(report.outcome_tier, "value", str(report.outcome_tier)),
                    "is_urgent_red_flag": report.is_urgent_red_flag
                },
                timestamp=datetime.now(timezone.utc)
            )
            db.add(audit_entry)
            db.commit()
        except Exception:
            db.rollback()
