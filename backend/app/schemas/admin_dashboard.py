from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, EmailStr
from app.core.security import RoleEnum


class AdminAuditLogItem(BaseModel):
    id: int
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    user_role: Optional[str] = None
    action: str
    resource_type: str
    resource_id: str
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    timestamp: datetime


class AdminOverviewResponse(BaseModel):
    users_total: int
    users_active: int
    users_inactive: int
    users_by_role: Dict[str, int]
    assessments_total: int
    assessments_by_status: Dict[str, int]
    reports_total: int
    reports_withheld_count: int
    clinician_reviews_pending: int
    clinician_reviews_in_progress: int
    clinician_reviews_completed: int
    recent_admin_activity: List[AdminAuditLogItem]
    platform_health_status: str  # "HEALTHY", "DEGRADED", "ERROR"
    clinical_governance_status: str  # "WITHHELD - PENDING CLINICAL BOARD REVIEW"
    governance_warning: str


class AdminUserListItem(BaseModel):
    id: int
    email: str
    full_name: str
    role: RoleEnum
    credentials_summary: Optional[str] = None
    is_active: bool
    created_at: datetime


class AdminUserListResponse(BaseModel):
    items: List[AdminUserListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdminUserDetailResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: RoleEnum
    credentials_summary: Optional[str] = None
    is_active: bool
    created_at: datetime
    assessments_count: int
    recent_audit_logs: List[AdminAuditLogItem]


class AdminUserStatusUpdateRequest(BaseModel):
    is_active: bool
    reason: Optional[str] = Field(None, max_length=500)


class AdminUserRoleUpdateRequest(BaseModel):
    role: RoleEnum
    reason: Optional[str] = Field(None, max_length=500)


class AdminAssessmentStatsResponse(BaseModel):
    total_assessments: int
    status_counts: Dict[str, int]
    reports_generated: int
    incomplete_assessments: int
    withheld_clinical_results: int
    outcome_tier_counts: Dict[str, int]
    governance_withheld_percent: float


class AdminClinicianOperationsResponse(BaseModel):
    registered_clinicians: int
    active_clinicians: int
    shared_review_pool: bool = True
    exclusive_locking_implemented: bool = False
    pending_reviews: int
    in_review_count: int
    completed_reviews: int
    recent_reviews: List[Dict[str, Any]]


class AdminAuditEventListResponse(BaseModel):
    items: List[AdminAuditLogItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    storage_type: str = "APPLICATION_LEVEL_APPEND_ONLY"
    immutable_hardware_enforced: bool = False


class AdminHealthResponse(BaseModel):
    status: str
    database: Dict[str, Any]
    api_version: str
    ai_provider_mode: str
    ai_provider_configured: bool
    gemini_live_egress_active: bool = False
    clinical_governance_gate: str
    timestamp: datetime


class AdminConfigResponse(BaseModel):
    environment: str
    project_name: str
    api_v1_str: str
    allowed_cors_origins: List[str]
    rate_limit_per_minute: int
    auth_jwt_algorithm: str
    ai_provider_mode: str
    shared_review_queue: bool = True
