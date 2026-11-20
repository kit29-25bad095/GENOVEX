from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.questionnaire import Assessment
from app.models.assessment_report import AssessmentReport
from app.schemas.assessment_report import (
    AssessmentReportResponse, AssessmentHistoryResponse, AssessmentHistoryItem
)
from app.services.assessment_processing_service import AssessmentProcessingService, ClinicalGovernanceGate
from app.services.report_pdf_service import ReportPDFService
from app.core.security import get_current_user_optional, get_current_user, User, AuditLog

router = APIRouter(prefix="/assessment", tags=["Assessment Evaluation & Reports"])

@router.get("/history", response_model=AssessmentHistoryResponse, summary="Get user assessment history")
def get_user_assessment_history(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves chronological assessment history and historical report references for the authenticated user.
    Enforces strict IDOR protection: Users can only view assessments tied to their own user ID.
    """
    total = db.query(Assessment).filter(Assessment.user_id == current_user.id).count()
    assessments = (
        db.query(Assessment)
        .filter(Assessment.user_id == current_user.id)
        .order_by(desc(Assessment.started_at))
        .offset(offset)
        .limit(limit)
        .all()
    )

    items: List[AssessmentHistoryItem] = []
    for a in assessments:
        report = db.query(AssessmentReport).filter(AssessmentReport.assessment_id == a.id).first()
        status_val = a.status.value if hasattr(a.status, "value") else str(a.status)
        tier_val = (
            getattr(report.outcome_tier, "value", str(report.outcome_tier))
            if report and report.outcome_tier
            else None
        )
        items.append(
            AssessmentHistoryItem(
                assessment_id=a.id,
                session_token=a.session_token,
                status=status_val,
                started_at=a.started_at,
                submitted_at=a.submitted_at,
                report_reference=report.report_reference if report else None,
                outcome_tier=tier_val,
                outcome_title_en=report.outcome_title_en if report else None,
                outcome_title_ar=report.outcome_title_ar if report else None,
                is_urgent_red_flag=report.is_urgent_red_flag if report else False,
                questionnaire_version_tag=report.questionnaire_version_tag if report else None,
                rule_engine_version=report.rule_engine_version if report else None,
            )
        )

    return AssessmentHistoryResponse(items=items, total=total)

@router.post("/{session_token}/claim", summary="Claim guest assessment to user account")
def claim_assessment(
    session_token: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Associates an anonymous/guest assessment session and its compiled report with the authenticated user profile.
    Prevents claiming assessments that are already owned by another registered user.
    """
    assessment = db.query(Assessment).filter(Assessment.session_token == session_token).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment session not found")

    if assessment.user_id is not None and assessment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Assessment is already linked to another user account"
        )

    assessment.user_id = current_user.id
    report = db.query(AssessmentReport).filter(AssessmentReport.assessment_id == assessment.id).first()
    if report:
        report.user_id = current_user.id

    try:
        audit_entry = AuditLog(
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
            action="CLAIM_ASSESSMENT",
            resource_type="Assessment",
            resource_id=assessment.id,
            details={"session_token": session_token},
            timestamp=datetime.now(timezone.utc)
        )
        db.add(audit_entry)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to link assessment to account")

    return {
        "status": "success",
        "message": "Assessment successfully linked to your account",
        "assessment_id": assessment.id,
        "session_token": session_token
    }

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

@router.get("/{session_token}/report/pdf", summary="Download official evidence-linked PDF report")
def download_assessment_report_pdf(
    session_token: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Generates and streams an official, downloadable bilingual PDF clinical assessment report.
    Enforces centralized clinical governance withholding and strict user ownership verification.
    """
    report = db.query(AssessmentReport).filter(AssessmentReport.session_token == session_token).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment report snapshot not found"
        )

    assessment = db.query(Assessment).filter(Assessment.id == report.assessment_id).first()
    if assessment:
        ClinicalGovernanceGate.verify_assessment_ownership(
            assessment=assessment,
            current_user=current_user,
            session_token=session_token
        )

    # Enforce centralized governance gate (returns HTTP 422 if rules unapproved for patient routes)
    ClinicalGovernanceGate.verify_report_access(
        db=db,
        report=report,
        current_user=current_user,
        assessment=assessment
    )

    pdf_bytes = ReportPDFService.generate_pdf_report(report=report, user=current_user)

    # Log categorical audit trail
    try:
        audit_entry = AuditLog(
            user_id=current_user.id if current_user else report.user_id,
            action="DOWNLOAD_ASSESSMENT_REPORT_PDF",
            resource_type="AssessmentReport",
            resource_id=report.report_reference,
            details={"report_reference": report.report_reference, "byte_size": len(pdf_bytes)},
            timestamp=datetime.now(timezone.utc)
        )
        db.add(audit_entry)
        db.commit()
    except Exception:
        db.rollback()

    filename = f"GENOVEX-Report-{report.report_reference}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate"
        }
    )
