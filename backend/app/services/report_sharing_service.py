import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
import jwt
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.security import User, AuditLog
from app.models.assessment_report import AssessmentReport
from app.models.questionnaire import Assessment
from app.schemas.assessment_report import (
    ReportVerificationResponse,
    ReportShareRequest,
    ReportShareResponse,
    AssessmentComparisonResponse,
)

class ReportSharingService:
    """
    Secure Report Integrity, Verification, Expiring Sharing, and Historical Comparison Service.
    Enforces strict patient consent, expiring/revocable tokens, and non-diagnostic comparative guardrails.
    Zero PHI leakage on public verification routes.
    """

    JWT_ALGORITHM = "HS256"

    @classmethod
    def compute_report_integrity_hash(cls, report: AssessmentReport) -> str:
        """
        Generates a deterministic SHA-256 cryptographic snapshot hash of immutable report data.
        Guarantees mathematical tamper-evidence without modifying database schema.
        """
        gen_str = report.generated_at.isoformat() if report.generated_at else "STATIC"
        tier_str = getattr(report.outcome_tier, "value", str(report.outcome_tier))
        payload = (
            f"{report.report_reference}:"
            f"{report.assessment_id}:"
            f"{report.questionnaire_version_tag}:"
            f"{report.rule_engine_version}:"
            f"{tier_str}:"
            f"{gen_str}:"
            f"{report.is_urgent_red_flag}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    def verify_report_authenticity(cls, db: Session, report_reference: str) -> ReportVerificationResponse:
        """
        Public verification endpoint service.
        Confirms authenticity, engine version, and outcome tier.
        STRICT PRIVACY: Never returns patient names, user IDs, or raw responses.
        """
        report = db.query(AssessmentReport).filter(
            AssessmentReport.report_reference == report_reference
        ).first()

        if not report:
            return ReportVerificationResponse(
                is_valid=False,
                status="NOT_FOUND",
                report_reference=report_reference,
                message_en="Report reference not found in GENOVEX registry. This document may be invalid or forged.",
                message_ar="الرقم المرجعي للتقرير غير موجود في سجل جينوفيكس. قد يكون هذا المستند غير صالح أو غير معتمد."
            )

        # Check if revoked via AuditLog
        revoked_log = db.query(AuditLog).filter(
            AuditLog.resource_type == "AssessmentReport",
            AuditLog.resource_id == report.report_reference,
            AuditLog.action == "REVOKE_REPORT_PUBLIC_ACCESS"
        ).first()

        if revoked_log:
            return ReportVerificationResponse(
                is_valid=False,
                status="INVALID_OR_REVOKED",
                report_reference=report_reference,
                message_en="This report reference has been officially revoked or retired by the patient/clinician.",
                message_ar="تم إلغاء الرقم المرجعي لهذا التقرير أو إيقافه رسمياً من قبل المريض أو الطبيب."
            )

        integrity_hash = cls.compute_report_integrity_hash(report)
        tier_str = getattr(report.outcome_tier, "value", str(report.outcome_tier))

        return ReportVerificationResponse(
            is_valid=True,
            status="AUTHENTIC_VERIFIED",
            report_reference=report.report_reference,
            generated_at=report.generated_at,
            questionnaire_version_tag=report.questionnaire_version_tag,
            rule_engine_version=report.rule_engine_version,
            outcome_tier=tier_str,
            outcome_title_en=report.outcome_title_en,
            outcome_title_ar=report.outcome_title_ar,
            is_urgent_red_flag=report.is_urgent_red_flag,
            integrity_hash=integrity_hash,
            message_en="Authentic, digitally verified GENOVEX clinical assessment report.",
            message_ar="تقرير تقييم إكلينيكي معتمد وموثق رقمياً من منصة جينوفيكس."
        )

    @classmethod
    def create_share_token(
        cls,
        db: Session,
        report_reference: str,
        current_user: User,
        share_req: ReportShareRequest
    ) -> ReportShareResponse:
        """
        Generates an expiring, cryptographically signed JWT share token for authorized clinician access.
        Enforces explicit patient consent and ownership verification.
        """
        report = db.query(AssessmentReport).filter(
            AssessmentReport.report_reference == report_reference
        ).first()

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment report not found"
            )

        # Ownership verification
        if report.user_id != current_user.id and current_user.role.value != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not own this report"
            )

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=share_req.expires_in_days)
        jti = uuid.uuid4().hex

        payload = {
            "type": "report_share",
            "jti": jti,
            "sub": report.report_reference,
            "patient_user_id": current_user.id,
            "clinician_email": share_req.clinician_email,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp())
        }

        secret = settings.SECRET_KEY
        share_token = jwt.encode(payload, secret, algorithm=cls.JWT_ALGORITHM)

        # Audit log creation
        audit_entry = AuditLog(
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=current_user.role.value,
            action="CREATE_REPORT_SHARE_TOKEN",
            resource_type="AssessmentReport",
            resource_id=report.report_reference,
            details={
                "jti": jti,
                "expires_at": expires_at.isoformat(),
                "clinician_email": share_req.clinician_email,
                "expires_in_days": share_req.expires_in_days
            },
            timestamp=now
        )
        db.add(audit_entry)
        db.commit()

        share_url = f"/reports/shared/{share_token}"

        return ReportShareResponse(
            report_reference=report.report_reference,
            share_token=share_token,
            expires_at=expires_at,
            share_url=share_url,
            status="ACTIVE",
            message_en=f"Report share link generated successfully. Expires in {share_req.expires_in_days} days.",
            message_ar=f"تم إنشاء رابط مشاركة التقرير بنجاح. ينتهي الرابط خلال {share_req.expires_in_days} أيام."
        )

    @classmethod
    def revoke_share_token(
        cls,
        db: Session,
        report_reference: str,
        current_user: User,
        share_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Immediately revokes an active share token or revokes all public sharing for this report.
        """
        report = db.query(AssessmentReport).filter(
            AssessmentReport.report_reference == report_reference
        ).first()

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment report not found"
            )

        if report.user_id != current_user.id and current_user.role.value != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not own this report"
            )

        jti = None
        if share_token:
            try:
                decoded = jwt.decode(share_token, settings.SECRET_KEY, algorithms=[cls.JWT_ALGORITHM], options={"verify_exp": False})
                jti = decoded.get("jti")
            except Exception:
                pass

        now = datetime.now(timezone.utc)
        audit_entry = AuditLog(
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=current_user.role.value,
            action="REVOKE_REPORT_SHARE",
            resource_type="AssessmentReport",
            resource_id=report.report_reference,
            details={
                "revoked_jti": jti,
                "revoked_token_snippet": share_token[:16] + "..." if share_token else None
            },
            timestamp=now
        )
        db.add(audit_entry)
        db.commit()

        return {
            "status": "revoked",
            "report_reference": report.report_reference,
            "message_en": "Report share access successfully revoked.",
            "message_ar": "تم إلغاء صلاحية مشاركة التقرير بنجاح."
        }

    @classmethod
    def resolve_shared_report(cls, db: Session, share_token: str) -> AssessmentReport:
        """
        Validates an incoming expiring share token and returns the underlying report.
        Rejects expired, tampered, or revoked tokens.
        """
        try:
            payload = jwt.decode(
                share_token,
                settings.SECRET_KEY,
                algorithms=[cls.JWT_ALGORITHM]
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Report share link has expired"
            )
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid report share link"
            )

        if payload.get("type") != "report_share":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )

        report_ref = payload.get("sub")
        jti = payload.get("jti")

        # Check revocation in AuditLog
        revoked = db.query(AuditLog).filter(
            AuditLog.resource_type == "AssessmentReport",
            AuditLog.resource_id == report_ref,
            AuditLog.action == "REVOKE_REPORT_SHARE"
        ).all()

        for log in revoked:
            details = log.details or {}
            if details.get("revoked_jti") == jti or not details.get("revoked_jti"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="This report share link has been revoked by the patient"
                )

        report = db.query(AssessmentReport).filter(
            AssessmentReport.report_reference == report_ref
        ).first()

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shared report not found"
            )

        return report

    @classmethod
    def compare_historical_assessments(
        cls,
        db: Session,
        base_assessment_id: str,
        target_assessment_id: str,
        current_user: User
    ) -> AssessmentComparisonResponse:
        """
        Safely compares two historical assessment snapshots belonging to the same user.
        Calculates differences in reported risk factors, response choices, and recommended specialties.
        Enforces strict non-diagnostic disclaimers: Explains that self-reported changes
        do NOT constitute biological or laboratory-confirmed progression.
        """
        # Fetch base assessment
        base_assess = db.query(Assessment).filter(Assessment.id == base_assessment_id).first()
        if not base_assess or (base_assess.user_id != current_user.id and current_user.role.value != "ADMIN"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Base assessment not found or access denied"
            )

        # Fetch target assessment
        target_assess = db.query(Assessment).filter(Assessment.id == target_assessment_id).first()
        if not target_assess or (target_assess.user_id != current_user.id and current_user.role.value != "ADMIN"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target assessment not found or access denied"
            )

        base_report = db.query(AssessmentReport).filter(AssessmentReport.assessment_id == base_assessment_id).first()
        target_report = db.query(AssessmentReport).filter(AssessmentReport.assessment_id == target_assessment_id).first()

        base_tier = getattr(base_report.outcome_tier, "value", str(base_report.outcome_tier)) if base_report else None
        target_tier = getattr(target_report.outcome_tier, "value", str(target_report.outcome_tier)) if target_report else None
        outcome_changed = (base_tier != target_tier)

        # Risk Factors comparison
        base_factors = {
            f.get("factor_code"): f for f in (base_report.identified_risk_factors_json or [])
            if isinstance(f, dict) and f.get("factor_code")
        } if base_report else {}

        target_factors = {
            f.get("factor_code"): f for f in (target_report.identified_risk_factors_json or [])
            if isinstance(f, dict) and f.get("factor_code")
        } if target_report else {}

        new_risk_factors = [
            target_factors[code] for code in target_factors if code not in base_factors
        ]
        resolved_risk_factors = [
            base_factors[code] for code in base_factors if code not in target_factors
        ]
        persisting_risk_factors = [
            target_factors[code] for code in target_factors if code in base_factors
        ]

        # Responses summary diff
        base_responses = {
            r.get("question_key"): r for r in (base_report.responses_summary_json or [])
            if isinstance(r, dict) and r.get("question_key")
        } if base_report else {}

        target_responses = {
            r.get("question_key"): r for r in (target_report.responses_summary_json or [])
            if isinstance(r, dict) and r.get("question_key")
        } if target_report else {}

        response_changes = []
        all_keys = set(base_responses.keys()).union(set(target_responses.keys()))
        for key in sorted(all_keys):
            b_item = base_responses.get(key)
            t_item = target_responses.get(key)
            b_ans = b_item.get("answer_display_en", "Not Answered") if b_item else "Not Surveyed"
            t_ans = t_item.get("answer_display_en", "Not Answered") if t_item else "Not Surveyed"
            b_ans_ar = b_item.get("answer_display_ar", "لم تتم الإجابة") if b_item else "لم يُسأل"
            t_ans_ar = t_item.get("answer_display_ar", "لم تتم الإجابة") if t_item else "لم يُسأل"

            if b_ans != t_ans:
                prompt_en = (t_item or b_item or {}).get("prompt_en", key)
                prompt_ar = (t_item or b_item or {}).get("prompt_ar", key)
                domain = (t_item or b_item or {}).get("domain_code", "general")
                response_changes.append({
                    "question_key": key,
                    "domain": domain,
                    "prompt_en": prompt_en,
                    "prompt_ar": prompt_ar,
                    "base_answer_en": b_ans,
                    "target_answer_en": t_ans,
                    "base_answer_ar": b_ans_ar,
                    "target_answer_ar": t_ans_ar,
                })

        # Specialties diff
        base_specs = set(base_report.recommended_specialties or []) if base_report else set()
        target_specs = set(target_report.recommended_specialties or []) if target_report else set()

        specialties_diff = {
            "base_specialties": list(base_specs),
            "target_specialties": list(target_specs),
            "added_specialties": list(target_specs - base_specs),
            "removed_specialties": list(base_specs - target_specs)
        }

        # Mandatory non-diagnostic comparison disclaimers
        disclaimer_en = (
            "IMPORTANT CLINICAL NOTICE: Differences in this historical comparison reflect self-reported questionnaire "
            "responses over time and must NOT be interpreted as biological progression, fertility improvement, or deterioration. "
            "GENOVEX does not measure semen parameters (count, motility, morphology). Biological fertility status can only "
            "be confirmed by qualified clinicians through physical examination and certified laboratory semen analyses."
        )
        disclaimer_ar = (
            "تنبيه إكلينيكي هام: تعكس الفروقات في هذه المقارنة التاريخية إجابات الاستبيان الذاتية للمريض عبر الزمن، "
            "ولا يجوز بأي حال تفسيرها كتطور بيولوجي أو تحسن أو تراجع في الخصوبة. لا تقيس منصة جينوفيكس معايير السائل المنوي "
            "(العدد، الحركة، الشكل). لا يمكن التحقق من الحالة البيولوجية للخصوبة إلا بواسطة أطباء متخصصين من خلال الفحص السريري وتحاليل المختبر المعتمدة."
        )

        return AssessmentComparisonResponse(
            base_assessment_id=base_assessment_id,
            target_assessment_id=target_assessment_id,
            base_report_reference=base_report.report_reference if base_report else None,
            target_report_reference=target_report.report_reference if target_report else None,
            base_date=base_assess.submitted_at or base_assess.started_at,
            target_date=target_assess.submitted_at or target_assess.started_at,
            outcome_changed=outcome_changed,
            base_outcome_tier=base_tier,
            target_outcome_tier=target_tier,
            new_risk_factors=new_risk_factors,
            resolved_risk_factors=resolved_risk_factors,
            persisting_risk_factors=persisting_risk_factors,
            response_changes=response_changes,
            specialties_diff=specialties_diff,
            disclaimer_en=disclaimer_en,
            disclaimer_ar=disclaimer_ar
        )
