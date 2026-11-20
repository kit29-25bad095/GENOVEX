from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class AIMetadata(BaseModel):
    """Operational traceability metadata captured without sensitive clinical content."""
    provider: str
    model: str
    prompt_version: str = "v1.0.0"
    request_id: str
    timestamp: str
    is_educational: bool = True
    disclaimer: str = (
        "GENOVEX AI provides educational context and terminology assistance only. "
        "It does not provide medical diagnoses, treatment plans, or fertility probabilities."
    )


class HealthEducationRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=500, description="Health or lifestyle topic to explain")
    context: Optional[str] = Field(None, max_length=1000, description="Optional educational context")
    language: str = Field("en", description="Target language ('en' or 'ar')")


class HealthEducationResponse(BaseModel):
    topic: str
    title: str
    explanation: str
    key_points: List[str] = Field(default_factory=list)
    guideline_sources: List[str] = Field(default_factory=list)
    metadata: AIMetadata


class TerminologyExplanationRequest(BaseModel):
    term: str = Field(..., min_length=2, max_length=150, description="Medical term to clarify")
    language: str = Field("en", description="Target language ('en' or 'ar')")


class TerminologyExplanationResponse(BaseModel):
    term: str
    plain_language_definition: str
    clinical_context: str
    common_misconceptions: Optional[str] = None
    metadata: AIMetadata


class ResultExplanationRequest(BaseModel):
    report_reference: str = Field(..., min_length=5, max_length=100, description="Report reference string")
    session_token: Optional[str] = Field(None, max_length=100)
    language: str = Field("en", description="Target language ('en' or 'ar')")


class ResultExplanationResponse(BaseModel):
    report_reference: str
    outcome_tier: str
    plain_language_summary: str
    identified_factors_explained: List[Dict[str, str]] = Field(default_factory=list)
    next_steps_explained: List[str] = Field(default_factory=list)
    non_diagnostic_notice: str
    metadata: AIMetadata


class PreparationQuestionsRequest(BaseModel):
    report_reference: str = Field(..., min_length=5, max_length=100)
    session_token: Optional[str] = Field(None, max_length=100)
    language: str = Field("en")


class PreparationQuestionsResponse(BaseModel):
    report_reference: str
    questions_for_clinician: List[str] = Field(default_factory=list)
    suggested_specialties: List[str] = Field(default_factory=list)
    recommended_documents_to_bring: List[str] = Field(default_factory=list)
    metadata: AIMetadata


class ClinicianSummaryRequest(BaseModel):
    assessment_id: str = Field(..., min_length=10, max_length=100)
    focus_areas: Optional[List[str]] = Field(default_factory=list)


class ClinicianSummaryResponse(BaseModel):
    assessment_id: str
    patient_reference: str
    clinical_triage_tier: str
    is_urgent_red_flag: bool
    response_overview: Dict[str, Any]
    synthesized_risk_narrative: str
    suggested_diagnostic_workup: List[str] = Field(default_factory=list)
    is_ai_generated: bool = True
    metadata: AIMetadata
