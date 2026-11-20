from datetime import datetime
import json
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator

class FacilityBase(BaseModel):
    name_en: str
    name_ar: str
    emirate: str  # DUBAI, ABU_DHABI, SHARJAH, AJMAN, RAK, UAQ, FUJAIRAH
    regulatory_authority: str  # DHA, DOH, MOHAP
    facility_type: str  # TERTIARY_HOSPITAL, SPECIALIZED_ANDROLOGY_CENTER, FERTILITY_IVF_CENTER, GENERAL_HOSPITAL
    address_en: str
    address_ar: str
    city_en: str
    city_ar: str
    phone_number: str
    emergency_phone: Optional[str] = None
    website_url: Optional[str] = None
    booking_url: Optional[str] = None
    has_24_7_emergency: bool = False
    has_andrology_specialist: bool = False
    has_who_semen_analysis_lab: bool = False
    has_micro_tese_capability: bool = False
    offered_specialties: List[str] = Field(default_factory=list)
    insurance_networks: List[str] = Field(default_factory=list)
    is_verified: bool = True
    is_active: bool = True
    notes_en: Optional[str] = None
    notes_ar: Optional[str] = None

    @field_validator("offered_specialties", "insurance_networks", mode="before")
    @classmethod
    def parse_json_fields(cls, v):
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
        return v or []

class FacilityCreateRequest(FacilityBase):
    slug: str

class FacilityUpdateRequest(BaseModel):
    name_en: Optional[str] = None
    name_ar: Optional[str] = None
    emirate: Optional[str] = None
    regulatory_authority: Optional[str] = None
    facility_type: Optional[str] = None
    address_en: Optional[str] = None
    address_ar: Optional[str] = None
    city_en: Optional[str] = None
    city_ar: Optional[str] = None
    phone_number: Optional[str] = None
    emergency_phone: Optional[str] = None
    website_url: Optional[str] = None
    booking_url: Optional[str] = None
    has_24_7_emergency: Optional[bool] = None
    has_andrology_specialist: Optional[bool] = None
    has_who_semen_analysis_lab: Optional[bool] = None
    has_micro_tese_capability: Optional[bool] = None
    offered_specialties: Optional[List[str]] = None
    insurance_networks: Optional[List[str]] = None
    is_verified: Optional[bool] = None
    is_active: Optional[bool] = None
    notes_en: Optional[str] = None
    notes_ar: Optional[str] = None

class FacilityResponse(FacilityBase):
    id: int
    slug: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class FacilityListResponse(BaseModel):
    items: List[FacilityResponse]
    total: int
    page: int
    page_size: int
    emirates: List[str]
    specialties: List[str]

class NavigationRecommendationResponse(BaseModel):
    assessment_id: Optional[str] = None
    report_reference: Optional[str] = None
    outcome_tier: Optional[str] = None
    is_urgent_red_flag: bool = False
    recommended_specialties: List[str] = Field(default_factory=list)
    recommended_facilities: List[FacilityResponse] = Field(default_factory=list)
    emergency_facilities: List[FacilityResponse] = Field(default_factory=list)
    is_formal_referral: bool = False
    navigation_notice_en: str
    navigation_notice_ar: str
