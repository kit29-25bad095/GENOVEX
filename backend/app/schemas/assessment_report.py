from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, computed_field
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
    assessment_id: str
    session_token: Optional[str] = Field(None, exclude=True)
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
    identified_risk_factors: List[Dict[str, Any]] = Field(default_factory=list, validation_alias="identified_risk_factors_json", serialization_alias="identified_risk_factors")
    triggered_rules: List[Dict[str, Any]] = Field(default_factory=list, validation_alias="triggered_rules_snapshot_json", serialization_alias="triggered_rules")
    responses_summary: List[Dict[str, Any]] = Field(default_factory=list, validation_alias="responses_summary_json", serialization_alias="responses_summary")
    evidence_citations: List[Dict[str, Any]] = Field(default_factory=list, validation_alias="evidence_citations_json", serialization_alias="evidence_citations")
    clinical_disclaimer_en: str
    clinical_disclaimer_ar: str
    is_locked: bool
    generated_at: datetime

    @computed_field
    @property
    def overall_tier(self) -> str:
        val = self.outcome_tier.value if hasattr(self.outcome_tier, "value") else str(self.outcome_tier)
        mapping = {
            "NO_REPORTED_RISK_FACTORS": "ROUTINE_PREVENTIVE_CARE",
            "RISK_FACTORS_IDENTIFIED": "LIFESTYLE_MODIFIABLE_FACTORS",
            "CLINICAL_EVALUATION_RECOMMENDED": "SPECIALIST_EVALUATION_RECOMMENDED",
            "URGENT_MEDICAL_ASSESSMENT": "URGENT_MEDICAL_ASSESSMENT"
        }
        return mapping.get(val, val)

    @computed_field
    @property
    def has_urgent_flags(self) -> bool:
        return self.is_urgent_red_flag

    @computed_field
    @property
    def urgent_guidance(self) -> Optional[str]:
        return self.urgent_emergency_guidance_en

    @computed_field
    @property
    def non_diagnostic_summary_en(self) -> str:
        return self.outcome_description_en

    @computed_field
    @property
    def non_diagnostic_summary_ar(self) -> str:
        return self.outcome_description_ar

    @computed_field
    @property
    def created_at(self) -> str:
        return self.generated_at.isoformat() if self.generated_at else ""

    @computed_field
    @property
    def evaluation_completeness(self) -> str:
        if "INCOMPLETE EVALUATION" in (self.outcome_title_en or "").upper():
            return "INDETERMINATE"
        summary = self.responses_summary or []
        for item in summary:
            if item.get("is_unsure") or item.get("is_prefer_not_to_say") or item.get("is_missing"):
                return "INDETERMINATE"
        return "DETERMINATE"

    @computed_field
    @property
    def is_evaluation_incomplete(self) -> bool:
        return self.evaluation_completeness == "INDETERMINATE"

    @computed_field
    @property
    def is_amber_warning(self) -> bool:
        return self.is_evaluation_incomplete

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class AssessmentHistoryItem(BaseModel):
    assessment_id: str
    session_token: str
    status: str
    started_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    report_reference: Optional[str] = None
    outcome_tier: Optional[str] = None
    outcome_title_en: Optional[str] = None
    outcome_title_ar: Optional[str] = None
    is_urgent_red_flag: bool = False
    questionnaire_version_tag: Optional[str] = None
    rule_engine_version: Optional[str] = None

class AssessmentHistoryResponse(BaseModel):
    items: List[AssessmentHistoryItem]
    total: int
