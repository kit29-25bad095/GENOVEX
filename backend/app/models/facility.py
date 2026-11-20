from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, JSON
from app.core.database import Base

class HealthcareFacility(Base):
    """
    Healthcare Facility ORM Model.
    Represents specialized UAE and regional reproductive health centers,
    andrology clinics, and tertiary fertility facilities.
    """
    __tablename__ = "healthcare_facilities"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    name_en = Column(String(200), nullable=False)
    name_ar = Column(String(200), nullable=False)
    emirate = Column(String(14), nullable=False, index=True)
    regulatory_authority = Column(String(5), nullable=False, index=True)
    facility_type = Column(String(28), nullable=False, index=True)
    address_en = Column(String(300), nullable=False)
    address_ar = Column(String(300), nullable=False)
    city_en = Column(String(100), nullable=False)
    city_ar = Column(String(100), nullable=False)
    phone_number = Column(String(50), nullable=False)
    emergency_phone = Column(String(50), nullable=True)
    website_url = Column(String(255), nullable=True)
    booking_url = Column(String(255), nullable=True)
    has_24_7_emergency = Column(Boolean, default=False, nullable=False, index=True)
    has_andrology_specialist = Column(Boolean, default=False, nullable=False)
    has_who_semen_analysis_lab = Column(Boolean, default=False, nullable=False)
    has_micro_tese_capability = Column(Boolean, default=False, nullable=False)
    offered_specialties = Column(JSON, default=list, nullable=False)
    insurance_networks = Column(JSON, default=list, nullable=False)
    is_verified = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    notes_en = Column(Text, nullable=True)
    notes_ar = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
