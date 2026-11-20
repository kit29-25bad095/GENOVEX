from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
import enum


class ReviewWorkflowStatus(str, enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    IN_REVIEW = "IN_REVIEW"
    REVIEW_COMPLETED = "REVIEW_COMPLETED"
    FURTHER_INFO_REQUIRED = "FURTHER_INFO_REQUIRED"


class ClinicianAssessmentQueueItem(BaseModel):
    assessment_id: str
    patient_reference: str
    status: str
    outcome_tier: Optional[str] = None
    is_urgent_red_flag: bool = False
    review_workflow_status: str = ReviewWorkflowStatus.PENDING_REVIEW.value
    submitted_at: Optional[str] = None
    last_activity_at: str


class ClinicianDashboardSummaryResponse(BaseModel):
    clinician_id: int
    clinician_name: str
    credentials_summary: Optional[str] = None
    assigned_assessments_count: int
    pending_review_count: int
    in_review_count: int
    review_completed_count: int
    assessments_queue: List[ClinicianAssessmentQueueItem] = Field(default_factory=list)


class ClinicianAssessmentDetailResponse(BaseModel):
    assessment_id: str
    patient_reference: str
    status: str
    questionnaire_version_tag: str
    current_review_status: str
    submitted_at: Optional[str] = None
    responses: List[Dict[str, Any]] = Field(default_factory=list)
    deterministic_report: Optional[Dict[str, Any]] = None
    review_history: List[Dict[str, Any]] = Field(default_factory=list)
    has_unapproved_rules: bool = False
    is_evaluation_incomplete: bool = False


class ClinicianReviewStatusUpdateRequest(BaseModel):
    review_status: ReviewWorkflowStatus
    notes: Optional[str] = Field(None, max_length=2000)


class ClinicianReviewStatusResponse(BaseModel):
    assessment_id: str
    previous_status: str
    current_status: str
    updated_by_clinician_id: int
    updated_at: str
    audit_log_id: int


class ClinicianNoteCreateRequest(BaseModel):
    note_text: str = Field(..., min_length=2, max_length=5000)


class ClinicianNoteItem(BaseModel):
    note_id: int
    author_name: str
    author_role: str
    note_text: str
    created_at: str


class ClinicianAISummaryRequest(BaseModel):
    focus_areas: Optional[List[str]] = Field(default_factory=list)
