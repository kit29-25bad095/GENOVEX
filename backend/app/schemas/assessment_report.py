from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.models.clinical_rules import ClinicalOutcomeTier

class IdentifiedRiskFactorItem(BaseModel):
    factor_code: str
    domain: str
    title_en: str
    title_ar: str
    description_en: str
    description_ar: str
    severity: str = "MODERATE"  # MILD, MODERATE, HIGH, CRITICAL_URGENT
    clinical_specialty: Optional[str] = None
    guideline_sources: List[str] = Field(default_factory=list)

class TriggeredRuleItem(BaseModel):
    rule_code: str
    rule_version: str
    title_en: str
    title_ar: str
    outcome_tier: ClinicalOutcomeTier
    is_urgent_red_flag: bool
    clinical_rationale_en: str
    clinical_rationale_ar: str
    evidence_references: List[Dict[str, Any]] = Field(default_factory=list)

class ResponseSummaryItem(BaseModel):
    question_key: str
    domain_code: str
    prompt_en: str
    prompt_ar: str
    answer_display_en: str
    answer_display_ar: str
    is_unsure: bool = False
    is_prefer_not_to_say: bool = False
    is_missing: bool = False

class AssessmentReportResponse(BaseModel):
    id: int
    report_reference: str
    assessment_id: int
    session_token: str
    questionnaire_version_tag: str
    rule_engine_version: str
    outcome_tier: ClinicalOutcomeTier
    outcome_title_en: str
    outcome_title_ar: str
    outcome_description_en: str
    outcome_description_ar: str
    is_urgent_red_flag: bool
    urgent_emergency_guidance_en: Optional[str] = None
    urgent_emergency_guidance_ar: Optional[str] = None
    recommended_specialties: List[str] = Field(default_factory=list)
    recommended_next_steps_en: List[str] = Field(default_factory=list)
    recommended_next_steps_ar: List[str] = Field(default_factory=list)
    identified_risk_factors: List[Dict[str, Any]] = Field(default_factory=list, alias="identified_risk_factors_json")
    triggered_rules: List[Dict[str, Any]] = Field(default_factory=list, alias="triggered_rules_snapshot_json")
    responses_summary: List[Dict[str, Any]] = Field(default_factory=list, alias="responses_summary_json")
    evidence_citations: List[Dict[str, Any]] = Field(default_factory=list, alias="evidence_citations_json")
    clinical_disclaimer_en: str
    clinical_disclaimer_ar: str
    is_locked: bool
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
