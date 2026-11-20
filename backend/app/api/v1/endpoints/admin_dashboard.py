from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import User, RoleEnum, require_roles
from app.services.admin_dashboard_service import AdminDashboardService
from app.schemas.admin_dashboard import (
    AdminOverviewResponse, AdminUserListResponse, AdminUserDetailResponse,
    AdminUserListItem, AdminUserStatusUpdateRequest, AdminUserRoleUpdateRequest,
    AdminAssessmentStatsResponse, AdminClinicianOperationsResponse,
    AdminAuditEventListResponse, AdminHealthResponse, AdminConfigResponse
)

router = APIRouter(
    prefix="/admin",
    tags=["Admin - Platform Operations Dashboard"]
)


@router.get("/overview", response_model=AdminOverviewResponse, summary="Get operational platform overview")
def get_admin_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.SUPERADMIN]))
):
    """
    Returns platform overview metrics: user counts by role, assessment workflow distributions,
    report counts, clinician review statuses, recent admin activities, and health state.
    """
    return AdminDashboardService.get_overview(db, current_user)


@router.get("/users", response_model=AdminUserListResponse, summary="List platform users with filtering and search")
def list_admin_users(
    search: Optional[str] = Query(None, description="Search query by name or email"),
    role: Optional[RoleEnum] = Query(None, description="Filter by user role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.SUPERADMIN]))
):
    """Lists registered users with pagination, role filtering, search, and active status filtering."""
    return AdminDashboardService.list_users(
        db=db,
        current_user=current_user,
        search=search,
        role=role,
        is_active=is_active,
        page=page,
        page_size=page_size
    )


@router.get("/users/{user_id}", response_model=AdminUserDetailResponse, summary="Get user details and audit history")
def get_admin_user_detail(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.SUPERADMIN]))
):
    """Retrieves user profile details and recent audit logs associated with the user."""
    return AdminDashboardService.get_user_detail(db, user_id, current_user)


@router.patch("/users/{user_id}/status", response_model=AdminUserListItem, summary="Update user active/inactive status")
def update_admin_user_status(
    user_id: int,
    payload: AdminUserStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.SUPERADMIN]))
):
    """
    Activates or deactivates a user account.
    Enforces privilege boundaries:
    - ADMIN cannot deactivate a SUPERADMIN.
    - Cannot deactivate the final active SUPERADMIN.
    """
    return AdminDashboardService.update_user_status(
        db=db,
        user_id=user_id,
        is_active=payload.is_active,
        reason=payload.reason,
        current_user=current_user
    )


@router.patch("/users/{user_id}/role", response_model=AdminUserListItem, summary="Update user role")
def update_admin_user_role(
    user_id: int,
    payload: AdminUserRoleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.SUPERADMIN]))
):
    """
    Updates a user's role.
    Enforces privilege boundaries:
    - Self-role modification is strictly prohibited.
    - ADMIN cannot promote to SUPERADMIN.
    - ADMIN cannot modify a SUPERADMIN user.
    - Cannot demote the final active SUPERADMIN.
    """
    return AdminDashboardService.update_user_role(
        db=db,
        user_id=user_id,
        new_role=payload.role,
        reason=payload.reason,
        current_user=current_user
    )


@router.get("/assessments/stats", response_model=AdminAssessmentStatsResponse, summary="Get aggregate assessment statistics")
def get_admin_assessment_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.SUPERADMIN]))
):
    """Returns aggregate operational assessment metrics without patient answers or PII."""
    return AdminDashboardService.get_assessment_stats(db, current_user)


@router.get("/clinician-operations", response_model=AdminClinicianOperationsResponse, summary="Get clinician operational metrics")
def get_admin_clinician_operations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.SUPERADMIN]))
):
    """Returns operational metrics on clinician review queue and confirms shared review pool structure."""
    return AdminDashboardService.get_clinician_operations(db, current_user)


@router.get("/audit-events", response_model=AdminAuditEventListResponse, summary="Get paginated system audit events")
def get_admin_audit_events(
    action: Optional[str] = Query(None, description="Filter by audit action code"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    user_id: Optional[int] = Query(None, description="Filter by actor user ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.SUPERADMIN]))
):
    """Retrieves paginated audit events with action, resource, and actor filtering."""
    return AdminDashboardService.get_audit_events(
        db=db,
        current_user=current_user,
        action=action,
        resource_type=resource_type,
        user_id=user_id,
        page=page,
        page_size=page_size
    )


@router.get("/health", response_model=AdminHealthResponse, summary="Get platform operational health status")
def get_admin_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.SUPERADMIN]))
):
    """Returns platform operational health telemetry across database, API, and governance."""
    return AdminDashboardService.get_platform_health(db, current_user)


@router.get("/config", response_model=AdminConfigResponse, summary="Get safe platform configuration")
def get_admin_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.SUPERADMIN]))
):
    """Returns safe platform configuration parameters with all secrets redacted."""
    return AdminDashboardService.get_system_config(db, current_user)
