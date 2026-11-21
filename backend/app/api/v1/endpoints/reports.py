from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.questionnaire import Assessment
from app.models.assessment_report import AssessmentReport
from app.schemas.assessment_report import (
    AssessmentReportResponse,
    AssessmentHistoryResponse,
    AssessmentHistoryItem,
    ReportVerificationResponse,
    ReportShareRequest,
    ReportShareResponse,
    AssessmentComparisonResponse,
)
from app.services.report_sharing_service import ReportSharingService
from app.services.report_pdf_service import ReportPDFService
from app.services.assessment_processing_service import ClinicalGovernanceGate
from app.core.security import get_current_user_optional, get_current_user, User, AuditLog

router = APIRouter(tags=["Reports & Assessment History"])

# -----------------------------------------------------------------------------
# 1. Assessment History & Details (Plural /assessments routes)
# -----------------------------------------------------------------------------
@router.get("/assessments/history", response_model=AssessmentHistoryResponse, summary="Get user assessment history (Plural route)")
def get_user_assessment_history_plural(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves chronological assessment history for the authenticated user.
    Enforces strict IDOR protection.
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

@router.get("/assessments/compare", response_model=AssessmentComparisonResponse, summary="Safe historical assessment comparison")
def compare_assessments(
    base_id: str = Query(..., description="Base assessment ID"),
    target_id: str = Query(..., description="Target assessment ID to compare against"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Compares two historical assessments belonging to the authenticated user.
    Diffs outcomes, identified risk factors, response choices, and recommended specialties.
    Includes mandatory non-diagnostic disclaimers explaining that self-reported changes
    are not laboratory-confirmed biological changes.
    """
    return ReportSharingService.compare_historical_assessments(
        db=db,
        base_assessment_id=base_id,
        target_assessment_id=target_id,
        current_user=current_user
    )

@router.get("/assessments/{assessment_id}", summary="Get assessment metadata by ID")
def get_assessment_by_id(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves assessment record with strict ownership check (IDOR protection).
    """
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    if assessment.user_id != current_user.id and current_user.role.value != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    report = db.query(AssessmentReport).filter(AssessmentReport.assessment_id == assessment.id).first()

    return {
        "assessment_id": assessment.id,
        "session_token": assessment.session_token,
        "status": assessment.status.value if hasattr(assessment.status, "value") else str(assessment.status),
        "started_at": assessment.started_at,
        "submitted_at": assessment.submitted_at,
        "report_reference": report.report_reference if report else None,
        "outcome_tier": getattr(report.outcome_tier, "value", str(report.outcome_tier)) if report else None,
    }

@router.get("/assessments/{assessment_id}/report", response_model=AssessmentReportResponse, summary="Get assessment report by assessment ID")
def get_assessment_report_by_id(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves the compiled AssessmentReport snapshot by assessment ID.
    Enforces strict IDOR protection.
    """
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    if assessment.user_id != current_user.id and current_user.role.value != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    report = db.query(AssessmentReport).filter(AssessmentReport.assessment_id == assessment_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report snapshot not found")

    ClinicalGovernanceGate.verify_report_access(
        db=db,
        report=report,
        current_user=current_user,
        assessment=assessment
    )

    return report

# -----------------------------------------------------------------------------
# 2. Public Verification & Sharing Endpoints (/reports routes)
# -----------------------------------------------------------------------------
@router.get("/reports/{report_reference}/verify", response_model=ReportVerificationResponse, summary="Public report authenticity verification")
def verify_report_authenticity(
    report_reference: str,
    db: Session = Depends(get_db)
):
    """
    Public verification endpoint (accessible via QR code).
    Confirms authenticity and returns minimal non-sensitive verification data.
    ZERO PHI LEAKAGE: Never returns patient names, user IDs, or questionnaire responses.
    """
    return ReportSharingService.verify_report_authenticity(db=db, report_reference=report_reference)

@router.post("/reports/{report_reference}/share", response_model=ReportShareResponse, summary="Create secure expiring share link for clinician")
def create_report_share_token(
    report_reference: str,
    share_req: ReportShareRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generates a cryptographically signed expiring share token for authorized clinician access.
    Requires explicit patient ownership and creates an immutable audit trail.
    """
    return ReportSharingService.create_share_token(
        db=db,
        report_reference=report_reference,
        current_user=current_user,
        share_req=share_req
    )

@router.post("/reports/{report_reference}/revoke-share", summary="Revoke report share token")
def revoke_report_share(
    report_reference: str,
    share_token: Optional[str] = Query(None, description="Optional specific token to revoke"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Revokes access to a previously shared report link.
    """
    return ReportSharingService.revoke_share_token(
        db=db,
        report_reference=report_reference,
        current_user=current_user,
        share_token=share_token
    )

@router.get("/reports/{report_reference}/download", summary="Download official PDF report by report reference")
def download_report_pdf_by_reference(
    report_reference: str,
    share_token: Optional[str] = Query(None, description="Expiring share token for clinician access"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Streams the official bilingual PDF report by report reference.
    Can be accessed by:
    1. Authenticated report owner (patient)
    2. Authenticated clinician / admin
    3. Holder of a valid, unexpired, unrevoked share_token
    """
    report = db.query(AssessmentReport).filter(AssessmentReport.report_reference == report_reference).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report reference not found")

    assessment = db.query(Assessment).filter(Assessment.id == report.assessment_id).first()

    # If accessed via share token
    if share_token:
        # Validates token signature, expiration, and revocation
        ReportSharingService.resolve_shared_report(db=db, share_token=share_token)
    else:
        # Must be authenticated user or session owner
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required to download report")

        if assessment:
            ClinicalGovernanceGate.verify_assessment_ownership(
                assessment=assessment,
                current_user=current_user,
                session_token=report.session_token
            )

        ClinicalGovernanceGate.verify_report_access(
            db=db,
            report=report,
            current_user=current_user,
            assessment=assessment
        )

    pdf_bytes = ReportPDFService.generate_pdf_report(report=report, user=current_user)

    # Audit logging
    try:
        audit_entry = AuditLog(
            user_id=current_user.id if current_user else report.user_id,
            action="DOWNLOAD_REPORT_PDF_BY_REF",
            resource_type="AssessmentReport",
            resource_id=report.report_reference,
            details={"report_reference": report.report_reference, "byte_size": len(pdf_bytes), "via_share_token": bool(share_token)},
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

@router.get("/reports/shared/{share_token}", response_model=AssessmentReportResponse, summary="Access report via expiring clinician share link")
def get_shared_report(
    share_token: str,
    db: Session = Depends(get_db)
):
    """
    Enables authorized clinicians to view the finalized assessment report snapshot
    using an unexpired, unrevoked share token generated with explicit patient consent.
    """
    report = ReportSharingService.resolve_shared_report(db=db, share_token=share_token)

    # Log clinician/shared access audit event
    try:
        audit_entry = AuditLog(
            user_id=report.user_id,
            action="ACCESS_SHARED_REPORT",
            resource_type="AssessmentReport",
            resource_id=report.report_reference,
            details={"share_token_snippet": share_token[:16] + "..."},
            timestamp=datetime.now(timezone.utc)
        )
        db.add(audit_entry)
        db.commit()
    except Exception:
        db.rollback()

    return report
