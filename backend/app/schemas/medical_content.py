from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.models.medical_content import PublicationStatus, EvidenceClassification

# ----------------- Category Schemas -----------------
class MedicalCategoryBase(BaseModel):
    slug: str = Field(..., min_length=2, max_length=100)
    name_en: str = Field(..., min_length=2, max_length=150)
    name_ar: str = Field(..., min_length=2, max_length=150)
    description_en: Optional[str] = None
    description_ar: Optional[str] = None
    display_order: int = 0
    is_active: bool = True

class MedicalCategoryCreate(MedicalCategoryBase):
    pass

class MedicalCategoryUpdate(BaseModel):
    slug: Optional[str] = None
    name_en: Optional[str] = None
    name_ar: Optional[str] = None
    description_en: Optional[str] = None
    description_ar: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None

class MedicalCategoryResponse(MedicalCategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ----------------- Reference Schemas -----------------
class MedicalReferenceBase(BaseModel):
    title: str = Field(..., min_length=5, max_length=300)
    authors: Optional[str] = None
    journal_or_publisher: Optional[str] = None
    publication_year: Optional[int] = None
    doi_or_url: Optional[str] = None
    guideline_body: Optional[str] = None  # WHO, AUA, EAU, ASRM
    evidence_classification: str = EvidenceClassification.GUIDELINE_CONSENSUS.value

class MedicalReferenceCreate(MedicalReferenceBase):
    pass

class MedicalReferenceResponse(MedicalReferenceBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ----------------- Content Translation Schemas -----------------
class ConditionContentSchema(BaseModel):
    language: str = Field(..., pattern="^(en|ar)$", description="Language code: en or ar")
    name: str = Field(..., min_length=2, max_length=200)
    short_description: str = Field(..., min_length=10, max_length=500)
    detailed_explanation: str = Field(..., min_length=20)
    biological_mechanism: str = Field(..., min_length=20, description="Pathophysiology and biological mechanism")
    causes_and_risk_factors: str = Field(..., min_length=10)
    possible_symptoms: str = Field(..., min_length=10)
    silent_asymptomatic_presentation: str = Field(..., min_length=10, description="Silent/asymptomatic presentation warning")
    clinical_significance: str = Field(..., min_length=10)
    diagnostic_investigations: str = Field(..., min_length=10)
    clinical_next_steps: str = Field(..., min_length=10)

class ConditionContentResponse(ConditionContentSchema):
    id: int
    condition_id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ----------------- Condition Schemas -----------------
class MedicalConditionCreate(BaseModel):
    slug: str = Field(..., min_length=2, max_length=120)
    category_id: int
    organs_involved: List[str] = Field(default_factory=list)
    evidence_classification: str = "Level 1A"
    reference_ids: List[int] = Field(default_factory=list)
    en_content: ConditionContentSchema
    ar_content: ConditionContentSchema
    initial_status: PublicationStatus = PublicationStatus.DRAFT
    created_by: str = "Administrator"

class MedicalConditionUpdate(BaseModel):
    slug: Optional[str] = None
    category_id: Optional[int] = None
    organs_involved: Optional[List[str]] = None
    evidence_classification: Optional[str] = None
    reference_ids: Optional[List[int]] = None
    en_content: Optional[ConditionContentSchema] = None
    ar_content: Optional[ConditionContentSchema] = None
    change_summary: Optional[str] = "Updated condition content"
    modified_by: str = "Clinical Editor"

class MedicalConditionListItem(BaseModel):
    id: int
    slug: str
    category_id: int
    category_name_en: str
    category_name_ar: str
    name_en: str
    name_ar: str
    short_description_en: str
    short_description_ar: str
    organs_involved: List[str]
    evidence_classification: str
    publication_status: PublicationStatus
    current_version: int
    last_reviewed_at: Optional[datetime] = None
    clinical_reviewer: Optional[str] = None
    references_count: int = 0
    updated_at: datetime

class MedicalConditionResponse(BaseModel):
    id: int
    slug: str
    category: MedicalCategoryResponse
    organs_involved: List[str]
    evidence_classification: str
    publication_status: PublicationStatus
    current_version: int
    last_reviewed_at: Optional[datetime] = None
    clinical_reviewer: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    contents: List[ConditionContentResponse]
    references: List[MedicalReferenceResponse]
    model_config = ConfigDict(from_attributes=True)

# ----------------- Review & Versioning Schemas -----------------
class ClinicalReviewActionRequest(BaseModel):
    action: str = Field(..., description="SUBMIT_FOR_REVIEW | APPROVE | REJECT | PUBLISH | ARCHIVE")
    reviewer_name: str = Field(..., min_length=2)
    reviewer_role: str = Field(..., min_length=2)
    notes: Optional[str] = Field(None, description="Clinical feedback or reason for rejection/approval")

class ClinicalReviewRecordResponse(BaseModel):
    id: int
    condition_id: int
    version_number: int
    reviewer_name: str
    reviewer_role: str
    action: str
    notes: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ContentVersionResponse(BaseModel):
    id: int
    condition_id: int
    version_number: int
    change_summary: Optional[str] = None
    created_by: str
    created_at: datetime
    snapshot_data: Dict[str, Any]
    model_config = ConfigDict(from_attributes=True)

class RestoreVersionRequest(BaseModel):
    version_number: int = Field(..., ge=1)
    reason: str = Field(..., min_length=5)
    restored_by: str = Field(..., min_length=2)

# ----------------- Public Health Library Schemas -----------------
class PublicHealthLibraryItem(BaseModel):
    id: int
    slug: str
    category_slug: str
    category_name: str
    name: str
    short_description: str
    detailed_explanation: str
    organs_involved: List[str]
    biological_mechanism: str
    causes_and_risk_factors: str
    possible_symptoms: str
    silent_asymptomatic_presentation: str
    clinical_significance: str
    diagnostic_investigations: str
    clinical_next_steps: str
    evidence_classification: str
    references: List[MedicalReferenceResponse]
    current_version: int
    last_reviewed_at: Optional[datetime] = None
    clinical_reviewer: Optional[str] = None
    language: str
