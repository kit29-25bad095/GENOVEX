from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict
from app.models.questionnaire import (
    QuestionnaireStatus, QuestionDomain, QuestionType, AssessmentStatus
)

class QuestionOptionSchema(BaseModel):
    key: str
    label_en: str
    label_ar: str
    order: int = 0

class QuestionBase(BaseModel):
    domain_code: QuestionDomain
    question_key: str = Field(..., min_length=3, max_length=100)
    text_en: str = Field(..., min_length=5)
    text_ar: str = Field(..., min_length=5)
    help_text_en: Optional[str] = None
    help_text_ar: Optional[str] = None
    question_type: QuestionType
    options_json: List[QuestionOptionSchema] = Field(default_factory=list)
    is_required: bool = True
    allows_unsure: bool = True
    allows_prefer_not_to_say: bool = True
    clinical_rationale_en: str = Field(..., min_length=10)
    clinical_rationale_ar: str = Field(..., min_length=10)
    evidence_references: List[str] = Field(default_factory=list)
    display_order: int = 0
    is_urgent_red_flag: bool = False
    conditional_parent_key: Optional[str] = None
    conditional_trigger_values: Optional[List[Any]] = None

class QuestionCreate(QuestionBase):
    version_id: int

class QuestionUpdate(BaseModel):
    text_en: Optional[str] = None
    text_ar: Optional[str] = None
    help_text_en: Optional[str] = None
    help_text_ar: Optional[str] = None
    options_json: Optional[List[QuestionOptionSchema]] = None
    is_required: Optional[bool] = None
    allows_unsure: Optional[bool] = None
    allows_prefer_not_to_say: Optional[bool] = None
    clinical_rationale_en: Optional[str] = None
    clinical_rationale_ar: Optional[str] = None
    evidence_references: Optional[List[str]] = None
    display_order: Optional[int] = None
    is_urgent_red_flag: Optional[bool] = None
    conditional_parent_key: Optional[str] = None
    conditional_trigger_values: Optional[List[Any]] = None

class QuestionResponse(QuestionBase):
    id: int
    version_id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class QuestionnaireVersionBase(BaseModel):
    version_tag: str = Field(..., min_length=3, max_length=50) # e.g. "v1.0.0"
    title_en: str = Field(..., min_length=5, max_length=200)
    title_ar: str = Field(..., min_length=5, max_length=200)

class QuestionnaireVersionCreate(QuestionnaireVersionBase):
    pass

class QuestionnaireVersionResponse(QuestionnaireVersionBase):
    id: int
    status: QuestionnaireStatus
    published_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    clinical_reviewer_id: Optional[int] = None
    clinical_reviewer_notes: Optional[str] = None
    questions_count: int = 0
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ----------------- Assessment Engine Schemas -----------------
class AnswerInput(BaseModel):
    question_id: int
    question_key: str
    answer_value: Optional[Any] = None # can be bool, str, list, number
    is_unsure: bool = False
    is_prefer_not_to_say: bool = False

class AssessmentStartRequest(BaseModel):
    session_token: Optional[str] = None

class AssessmentStartResponse(BaseModel):
    assessment_id: str
    session_token: str
    questionnaire_version_id: int
    version_tag: str
    status: AssessmentStatus
    current_domain_index: int
    total_domains: int
    domains_meta: List[Dict[str, Any]]

class DomainQuestionsResponse(BaseModel):
    domain_code: QuestionDomain
    domain_index: int
    total_domains: int
    domain_title_en: str
    domain_title_ar: str
    questions: List[QuestionResponse]
    saved_answers: Dict[str, Any]

class SaveDomainResponsesRequest(BaseModel):
    domain_code: QuestionDomain
    answers: List[AnswerInput]
    next_domain_index: Optional[int] = None

class SaveDomainResponsesResponse(BaseModel):
    assessment_id: str
    saved_count: int
    current_domain_index: int
    progress_percentage: float
    urgent_red_flags_detected: List[str] = Field(default_factory=list)

class ReviewQuestionAnswerItem(BaseModel):
    question_id: int
    question_key: str
    domain_code: QuestionDomain
    text_en: str
    text_ar: str
    question_type: QuestionType
    answer_value: Optional[Any]
    is_unsure: bool
    is_prefer_not_to_say: bool
    is_answered: bool
    is_required: bool
    is_urgent_red_flag: bool
    options: List[QuestionOptionSchema]

class ReviewDomainGroup(BaseModel):
    domain_code: QuestionDomain
    domain_index: int
    domain_title_en: str
    domain_title_ar: str
    questions: List[ReviewQuestionAnswerItem]
    is_complete: bool

class AssessmentReviewResponse(BaseModel):
    assessment_id: str
    status: AssessmentStatus
    version_tag: str
    current_domain_index: int
    progress_percentage: float
    total_questions: int
    answered_count: int
    unanswered_required_count: int
    can_submit: bool
    domains: List[ReviewDomainGroup]
    urgent_red_flags: List[str]

class AssessmentSubmitResponse(BaseModel):
    assessment_id: str
    status: AssessmentStatus
    submitted_at: datetime
    version_tag: str
    has_urgent_red_flags: bool
    urgent_warning_en: Optional[str] = None
    urgent_warning_ar: Optional[str] = None
    message_en: str
    message_ar: str
