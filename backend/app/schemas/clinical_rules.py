from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, ConfigDict
from app.models.clinical_rules import ClinicalOutcomeTier, ClinicalRuleStatus
from app.models.questionnaire import QuestionDomain

class EvidenceReferenceItem(BaseModel):
    title: str = Field(..., description="Full title of scientific publication or guideline")
    guideline_body: str = Field(..., description="Authoring body: EAU, AUA, ASRM, WHO, etc.")
    year: int = Field(..., description="Publication year")
    doi_or_url: Optional[str] = Field(None, description="DOI link or authoritative URL")
    recommendation_text: Optional[str] = Field(None, description="Direct quote of clinical recommendation")
    review_date: Optional[str] = Field(None, description="Date evidence was reviewed by clinician")

class TriggerCriteriaPredicate(BaseModel):
    operator: str = Field(..., description="Comparison operator: equals, in, greater_than, less_than, contains")
    question_key: str = Field(..., description="Target question key from questionnaire")
    expected_value: Optional[Any] = Field(None, description="Value to match for equals / greater_than / less_than")
    expected_values: Optional[List[Any]] = Field(None, description="Values list for 'in' or 'contains' operators")

class ClinicalRuleBase(BaseModel):
    rule_code: str = Field(..., max_length=50, description="Unique code e.g. R-URG-SCROTAL-PAIN")
    title_en: str = Field(..., max_length=250)
    title_ar: str = Field(..., max_length=250)
    target_condition_slug: Optional[str] = None
    domain_code: QuestionDomain
    relevant_question_keys: List[str] = Field(default_factory=list)
    outcome_tier: ClinicalOutcomeTier
    is_urgent_red_flag: bool = False
    priority_rank: int = Field(default=100, ge=1, le=1000)
    recommended_specialty: Optional[str] = None
    trigger_criteria: Dict[str, Any]
    missing_response_handling: str = "NEVER_NEGATIVE"
    clinical_rationale_en: str
    clinical_rationale_ar: str
    evidence_references: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_classification: str = "Level 1a"

class ClinicalRuleCreate(ClinicalRuleBase):
    pass

class ClinicalRuleUpdate(BaseModel):
    title_en: Optional[str] = None
    title_ar: Optional[str] = None
    domain_code: Optional[QuestionDomain] = None
    relevant_question_keys: Optional[List[str]] = None
    outcome_tier: Optional[ClinicalOutcomeTier] = None
    is_urgent_red_flag: Optional[bool] = None
    priority_rank: Optional[int] = None
    recommended_specialty: Optional[str] = None
    trigger_criteria: Optional[Dict[str, Any]] = None
    missing_response_handling: Optional[str] = None
    clinical_rationale_en: Optional[str] = None
    clinical_rationale_ar: Optional[str] = None
    evidence_references: Optional[List[Dict[str, Any]]] = None
    evidence_classification: Optional[str] = None

class ClinicalRuleReviewAction(BaseModel):
    action: str = Field(..., description="'APPROVE' or 'REJECT'")
    reviewer_notes: str = Field(..., min_length=5, description="Clinical verification notes or required revisions")

class ClinicalRuleResponse(ClinicalRuleBase):
    id: int
    rule_version: str
    status: ClinicalRuleStatus
    created_by_user_id: Optional[int] = None
    clinical_reviewer_id: Optional[int] = None
    clinical_reviewer_notes: Optional[str] = None
    approved_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ClinicalRuleVersionResponse(BaseModel):
    id: int
    rule_id: int
    version_tag: str
    rule_code: str
    title_en: str
    title_ar: str
    outcome_tier: ClinicalOutcomeTier
    is_urgent_red_flag: bool
    trigger_criteria: Dict[str, Any]
    evidence_references: List[Dict[str, Any]]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
