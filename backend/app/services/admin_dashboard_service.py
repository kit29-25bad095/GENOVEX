from datetime import datetime, timezone
import math
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_, text
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.security import User, RoleEnum, AuditLog
from app.models.questionnaire import Assessment, AssessmentStatus
from app.models.assessment_report import AssessmentReport
from app.schemas.admin_dashboard import (
    AdminOverviewResponse, AdminUserListItem, AdminUserListResponse,
    AdminUserDetailResponse, AdminAssessmentStatsResponse,
    AdminClinicianOperationsResponse, AdminAuditEventListResponse,
    AdminHealthResponse, AdminConfigResponse, AdminAuditLogItem
)


class AdminDashboardService:
    """
    Centralized administrative dashboard service.
    Provides operational visibility, user/role management with strict privilege boundaries,
    aggregate assessment monitoring, clinician pool operations, and platform health telemetry.
    Adheres strictly to clinical governance separation: does NOT allow clinical rule modifications
    or unauthorized patient report releases.
    """

    @classmethod
    def _to_audit_item(cls, log: AuditLog) -> AdminAuditLogItem:
        # Sanitize details to ensure zero secrets or tokens
        safe_details = {}
        if log.details and isinstance(log.details, dict):
            for k, v in log.details.items():
                if any(secret_term in k.lower() for secret_term in ["token", "password", "key", "secret", "hash"]):
                    safe_details[k] = "[REDACTED]"
                else:
                    safe_details[k] = v
        else:
            safe_details = log.details

        return AdminAuditLogItem(
            id=log.id,
            user_id=log.user_id,
            user_email=log.user_email,
            user_role=log.user_role,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=str(log.resource_id),
            details=safe_details,
            ip_address=log.ip_address,
            timestamp=log.timestamp or datetime.now(timezone.utc)
        )

    @classmethod
    def get_overview(cls, db: Session, current_user: User) -> AdminOverviewResponse:
        """Computes aggregate operational summary for the administrative dashboard."""
        # 1. User metrics
        users_total = db.query(User).count()
        users_active = db.query(User).filter(User.is_active == True).count()
        users_inactive = db.query(User).filter(User.is_active == False).count()

        role_counts_raw = db.query(User.role, func.count(User.id)).group_by(User.role).all()
        users_by_role = {r.value if hasattr(r, "value") else str(r): 0 for r in RoleEnum}
        for r_val, count in role_counts_raw:
            key = r_val.value if hasattr(r_val, "value") else str(r_val)
            users_by_role[key] = count

        # 2. Assessment metrics
        assessments_total = db.query(Assessment).count()
        status_counts_raw = db.query(Assessment.status, func.count(Assessment.id)).group_by(Assessment.status).all()
        assessments_by_status = {}
        for s_val, count in status_counts_raw:
            key = s_val.value if hasattr(s_val, "value") else str(s_val)
            assessments_by_status[key] = count

        reports_total = db.query(AssessmentReport).count()
        # In fail-closed governance, 100% of reports are withheld from patients while rules lack clinical board sign-off
        reports_withheld_count = reports_total

        # 3. Clinician Review Queue metrics
        # Query latest status from AuditLog for assessments
        pending_reviews = 0
        in_progress_reviews = 0
        completed_reviews = 0

        submitted_assessments = db.query(Assessment.id).filter(
            Assessment.status.in_([AssessmentStatus.SUBMITTED, AssessmentStatus.LOCKED])
        ).all()

        for (a_id,) in submitted_assessments:
            latest_audit = db.query(AuditLog).filter(
                AuditLog.resource_type == "Assessment",
                AuditLog.resource_id == a_id,
                AuditLog.action == "CLINICIAN_REVIEW_WORKFLOW_UPDATE"
            ).order_by(desc(AuditLog.id)).first()

            if latest_audit and latest_audit.details:
                st = latest_audit.details.get("new_status")
                if st == "IN_REVIEW":
                    in_progress_reviews += 1
                elif st in ("REVIEWED", "REVIEW_COMPLETED"):
                    completed_reviews += 1
                else:
                    pending_reviews += 1
            else:
                pending_reviews += 1

        # 4. Recent administrative activity
        recent_logs = db.query(AuditLog).order_by(desc(AuditLog.id)).limit(8).all()
        recent_admin_activity = [cls._to_audit_item(log) for log in recent_logs]

        governance_warning = (
            "NOTICE: All 22 deterministic clinical rules are classified as UNAPPROVED due to lack of verified clinical board "
            "approval provenance. Patient-facing clinical results remain 100% WITHHELD across all 4 outcome tiers (HTTP 422). "
            "This dashboard provides operational administration and monitoring only, and does not authorize clinical release."
        )

        return AdminOverviewResponse(
            users_total=users_total,
            users_active=users_active,
            users_inactive=users_inactive,
            users_by_role=users_by_role,
            assessments_total=assessments_total,
            assessments_by_status=assessments_by_status,
            reports_total=reports_total,
            reports_withheld_count=reports_withheld_count,
            clinician_reviews_pending=pending_reviews,
            clinician_reviews_in_progress=in_progress_reviews,
            clinician_reviews_completed=completed_reviews,
            recent_admin_activity=recent_admin_activity,
            platform_health_status="HEALTHY",
            clinical_governance_status="WITHHELD - PENDING CLINICAL BOARD REVIEW",
            governance_warning=governance_warning
        )

    @classmethod
    def list_users(
        cls,
        db: Session,
        current_user: User,
        search: Optional[str] = None,
        role: Optional[RoleEnum] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20
    ) -> AdminUserListResponse:
        """Lists users with pagination, text search, role filtering, and status filtering."""
        page = max(1, page)
        page_size = min(max(1, page_size), 100)

        query = db.query(User)

        if search:
            search_clean = f"%{search.strip()}%"
            query = query.filter(or_(User.email.ilike(search_clean), User.full_name.ilike(search_clean)))

        if role:
            query = query.filter(User.role == role)

        if is_active is not None:
            query = query.filter(User.is_active == is_active)

        total = query.count()
        users = query.order_by(desc(User.created_at)).offset((page - 1) * page_size).limit(page_size).all()

        items = [
            AdminUserListItem(
                id=u.id,
                email=u.email,
                full_name=u.full_name,
                role=u.role,
                credentials_summary=u.credentials_summary,
                is_active=bool(u.is_active),
                created_at=u.created_at or datetime.now(timezone.utc)
            )
            for u in users
        ]

        total_pages = math.ceil(total / page_size) if total > 0 else 1

        return AdminUserListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    @classmethod
    def get_user_detail(cls, db: Session, user_id: int, current_user: User) -> AdminUserDetailResponse:
        """Retrieves user profile details and recent audit logs."""
        target_user = db.query(User).filter(User.id == user_id).first()
        if not target_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User ID {user_id} not found.")

        assessments_count = db.query(Assessment).filter(Assessment.user_id == user_id).count()
        recent_logs = db.query(AuditLog).filter(
            or_(AuditLog.user_id == user_id, AuditLog.resource_id == str(user_id))
        ).order_by(desc(AuditLog.id)).limit(10).all()

        return AdminUserDetailResponse(
            id=target_user.id,
            email=target_user.email,
            full_name=target_user.full_name,
            role=target_user.role,
            credentials_summary=target_user.credentials_summary,
            is_active=bool(target_user.is_active),
            created_at=target_user.created_at or datetime.now(timezone.utc),
            assessments_count=assessments_count,
            recent_audit_logs=[cls._to_audit_item(l) for l in recent_logs]
        )

    @classmethod
    def update_user_status(
        cls,
        db: Session,
        user_id: int,
        is_active: bool,
        reason: Optional[str],
        current_user: User
    ) -> AdminUserListItem:
        """
        Activates or deactivates a user account.
        Enforces privilege boundary:
        - ADMIN cannot deactivate a SUPERADMIN.
        - Cannot deactivate the final active SUPERADMIN on the platform.
        """
        target_user = db.query(User).filter(User.id == user_id).first()
        if not target_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User ID {user_id} not found.")

        # Privilege boundary: ADMIN cannot modify SUPERADMIN
        if current_user.role == RoleEnum.ADMIN and target_user.role == RoleEnum.SUPERADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: ADMIN role cannot modify account status of a SUPERADMIN."
            )

        # Final active SUPERADMIN lockout protection
        if target_user.role == RoleEnum.SUPERADMIN and not is_active:
            active_superadmins = db.query(User).filter(
                User.role == RoleEnum.SUPERADMIN,
                User.is_active == True
            ).count()
            if active_superadmins <= 1 and target_user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot deactivate the final active SUPERADMIN. Platform must retain at least one active SUPERADMIN."
                )

        old_status = target_user.is_active
        target_user.is_active = is_active

        # Record audit log
        audit = AuditLog(
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
            action="ADMIN_USER_STATUS_UPDATE",
            resource_type="User",
            resource_id=str(target_user.id),
            details={
                "previous_is_active": old_status,
                "new_is_active": is_active,
                "target_email": target_user.email,
                "target_role": target_user.role.value if hasattr(target_user.role, "value") else str(target_user.role),
                "reason": reason or "Administrative status adjustment"
            },
            timestamp=datetime.now(timezone.utc)
        )
        db.add(audit)
        db.commit()
        db.refresh(target_user)

        return AdminUserListItem(
            id=target_user.id,
            email=target_user.email,
            full_name=target_user.full_name,
            role=target_user.role,
            credentials_summary=target_user.credentials_summary,
            is_active=bool(target_user.is_active),
            created_at=target_user.created_at or datetime.now(timezone.utc)
        )

    @classmethod
    def update_user_role(
        cls,
        db: Session,
        user_id: int,
        new_role: RoleEnum,
        reason: Optional[str],
        current_user: User
    ) -> AdminUserListItem:
        """
        Updates a user's role with strict privilege boundary enforcement.
        Rules:
        - Self-role modification is strictly prohibited.
        - ADMIN cannot promote any user to SUPERADMIN.
        - ADMIN cannot modify the role of a SUPERADMIN.
        - Cannot demote the final active SUPERADMIN on the platform.
        """
        target_user = db.query(User).filter(User.id == user_id).first()
        if not target_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User ID {user_id} not found.")

        # Self-role modification protection
        if current_user.id == target_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Self-role modification is prohibited. Administrators cannot alter their own roles."
            )

        # ADMIN privilege boundaries
        if current_user.role == RoleEnum.ADMIN:
            if new_role == RoleEnum.SUPERADMIN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: ADMIN role cannot grant SUPERADMIN privileges."
                )
            if target_user.role == RoleEnum.SUPERADMIN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: ADMIN role cannot modify the role of a SUPERADMIN."
                )

        # Final active SUPERADMIN demotion protection
        if target_user.role == RoleEnum.SUPERADMIN and new_role != RoleEnum.SUPERADMIN:
            active_superadmins = db.query(User).filter(
                User.role == RoleEnum.SUPERADMIN,
                User.is_active == True
            ).count()
            if active_superadmins <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot demote the final active SUPERADMIN. Platform must retain at least one active SUPERADMIN."
                )

        old_role = target_user.role
        target_user.role = new_role

        audit = AuditLog(
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
            action="ADMIN_USER_ROLE_UPDATE",
            resource_type="User",
            resource_id=str(target_user.id),
            details={
                "previous_role": old_role.value if hasattr(old_role, "value") else str(old_role),
                "new_role": new_role.value if hasattr(new_role, "value") else str(new_role),
                "target_email": target_user.email,
                "reason": reason or "Administrative role assignment"
            },
            timestamp=datetime.now(timezone.utc)
        )
        db.add(audit)
        db.commit()
        db.refresh(target_user)

        return AdminUserListItem(
            id=target_user.id,
            email=target_user.email,
            full_name=target_user.full_name,
            role=target_user.role,
            credentials_summary=target_user.credentials_summary,
            is_active=bool(target_user.is_active),
            created_at=target_user.created_at or datetime.now(timezone.utc)
        )

    @classmethod
    def get_assessment_stats(cls, db: Session, current_user: User) -> AdminAssessmentStatsResponse:
        """Computes aggregate assessment workflow metrics without exposing patient PII."""
        total_assessments = db.query(Assessment).count()
        status_counts_raw = db.query(Assessment.status, func.count(Assessment.id)).group_by(Assessment.status).all()
        status_counts = {}
        for s_val, count in status_counts_raw:
            key = s_val.value if hasattr(s_val, "value") else str(s_val)
            status_counts[key] = count

        reports_generated = db.query(AssessmentReport).count()
        incomplete_assessments = db.query(Assessment).filter(Assessment.status == AssessmentStatus.IN_PROGRESS).count()
        withheld_clinical_results = reports_generated  # 100% withheld in current unapproved governance state

        tier_counts_raw = db.query(AssessmentReport.outcome_tier, func.count(AssessmentReport.id)).group_by(AssessmentReport.outcome_tier).all()
        outcome_tier_counts = {}
        for t_val, count in tier_counts_raw:
            key = t_val.value if hasattr(t_val, "value") else str(t_val)
            outcome_tier_counts[key] = count

        return AdminAssessmentStatsResponse(
            total_assessments=total_assessments,
            status_counts=status_counts,
            reports_generated=reports_generated,
            incomplete_assessments=incomplete_assessments,
            withheld_clinical_results=withheld_clinical_results,
            outcome_tier_counts=outcome_tier_counts,
            governance_withheld_percent=100.0
        )

    @classmethod
    def get_clinician_operations(cls, db: Session, current_user: User) -> AdminClinicianOperationsResponse:
        """Returns operational metrics for clinician queue and shared review pool."""
        registered_clinicians = db.query(User).filter(User.role == RoleEnum.CLINICIAN).count()
        active_clinicians = db.query(User).filter(User.role == RoleEnum.CLINICIAN, User.is_active == True).count()

        pending_count = 0
        in_review_count = 0
        completed_count = 0

        submitted = db.query(Assessment.id).filter(
            Assessment.status.in_([AssessmentStatus.SUBMITTED, AssessmentStatus.LOCKED])
        ).all()

        for (a_id,) in submitted:
            latest_audit = db.query(AuditLog).filter(
                AuditLog.resource_type == "Assessment",
                AuditLog.resource_id == a_id,
                AuditLog.action == "CLINICIAN_REVIEW_WORKFLOW_UPDATE"
            ).order_by(desc(AuditLog.id)).first()

            if latest_audit and latest_audit.details:
                st = latest_audit.details.get("new_status")
                if st == "IN_REVIEW":
                    in_review_count += 1
                elif st in ("REVIEWED", "REVIEW_COMPLETED"):
                    completed_count += 1
                else:
                    pending_count += 1
            else:
                pending_count += 1

        recent_audits = db.query(AuditLog).filter(
            AuditLog.action.like("CLINICIAN_%")
        ).order_by(desc(AuditLog.id)).limit(10).all()

        recent_reviews = [
            {
                "id": a.id,
                "action": a.action,
                "actor_email": a.user_email,
                "assessment_reference": f"PT-{a.resource_id[:8].upper()}" if a.resource_id else "UNKNOWN",
                "status": (a.details or {}).get("new_status", "UNKNOWN"),
                "timestamp": (a.timestamp or datetime.now(timezone.utc)).isoformat()
            }
            for a in recent_audits
        ]

        return AdminClinicianOperationsResponse(
            registered_clinicians=registered_clinicians,
            active_clinicians=active_clinicians,
            shared_review_pool=True,
            exclusive_locking_implemented=False,
            pending_reviews=pending_count,
            in_review_count=in_review_count,
            completed_reviews=completed_count,
            recent_reviews=recent_reviews
        )

    @classmethod
    def get_audit_events(
        cls,
        db: Session,
        current_user: User,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        user_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20
    ) -> AdminAuditEventListResponse:
        """Retrieves paginated audit events with action, resource, and actor filtering."""
        page = max(1, page)
        page_size = min(max(1, page_size), 100)

        query = db.query(AuditLog)

        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)

        total = query.count()
        logs = query.order_by(desc(AuditLog.id)).offset((page - 1) * page_size).limit(page_size).all()

        items = [cls._to_audit_item(l) for l in logs]
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        return AdminAuditEventListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            storage_type="APPLICATION_LEVEL_APPEND_ONLY",
            immutable_hardware_enforced=False
        )

    @classmethod
    def get_platform_health(cls, db: Session, current_user: User) -> AdminHealthResponse:
        """Evaluates platform operational health across database, API, AI mode, and governance."""
        db_connected = False
        sandbox_mode = False
        try:
            db.execute(text("SELECT 1;"))
            db_connected = True
            sandbox_mode = "sandbox" in settings.DATABASE_URL.lower() or "test" in settings.DATABASE_URL.lower()
        except Exception:
            db_connected = False

        ai_mode = getattr(settings, "AI_PROVIDER_MODE", "MOCK").upper()
        ai_configured = bool(getattr(settings, "GEMINI_API_KEY", None))

        overall_status = "HEALTHY" if db_connected else "DEGRADED"

        return AdminHealthResponse(
            status=overall_status,
            database={
                "connected": db_connected,
                "engine": "sqlite",
                "read_only": False,
                "sandbox_mode": sandbox_mode
            },
            api_version="1.0.0",
            ai_provider_mode=ai_mode,
            ai_provider_configured=ai_configured,
            gemini_live_egress_active=False,
            clinical_governance_gate="FAIL_CLOSED_ACTIVE",
            timestamp=datetime.now(timezone.utc)
        )

    @classmethod
    def get_system_config(cls, db: Session, current_user: User) -> AdminConfigResponse:
        """Returns safe system configuration parameters, strictly redacting all secrets."""
        from app.core.config import get_allowed_cors_origins

        ai_mode = getattr(settings, "AI_PROVIDER_MODE", "MOCK").upper()

        return AdminConfigResponse(
            environment=settings.ENVIRONMENT,
            project_name=settings.PROJECT_NAME,
            api_v1_str=settings.API_V1_STR,
            allowed_cors_origins=get_allowed_cors_origins(),
            rate_limit_per_minute=getattr(settings, "RATE_LIMIT_PER_MINUTE", 60),
            auth_jwt_algorithm="HS256",
            ai_provider_mode=ai_mode,
            shared_review_queue=True
        )
