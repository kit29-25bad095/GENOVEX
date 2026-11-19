from datetime import datetime, timezone
import enum
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, 
    Table, JSON, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from app.core.database import Base

class PublicationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"

class EvidenceClassification(str, enum.Enum):
    LEVEL_1A = "Level 1A (Systematic Review of RCTs)"
    LEVEL_1B = "Level 1B (Individual RCT)"
    LEVEL_2A = "Level 2A (Systematic Review of Cohort Studies)"
    LEVEL_2B = "Level 2B (Individual Cohort Study)"
    LEVEL_3 = "Level 3 (Case-Control Study)"
    LEVEL_4 = "Level 4 (Case Series / Clinical Consensus)"
    GUIDELINE_CONSENSUS = "Clinical Practice Guideline (WHO/AUA/EAU/ASRM)"

# Many-to-Many association between Conditions and References
condition_references = Table(
    "condition_references",
    Base.metadata,
    Column("condition_id", Integer, ForeignKey("medical_conditions.id", ondelete="CASCADE"), primary_key=True),
    Column("reference_id", Integer, ForeignKey("medical_references.id", ondelete="CASCADE"), primary_key=True)
)

class MedicalCategory(Base):
    __tablename__ = "medical_categories"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    name_en = Column(String(150), nullable=False)
    name_ar = Column(String(150), nullable=False)
    description_en = Column(Text, nullable=True)
    description_ar = Column(Text, nullable=True)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    conditions = relationship("MedicalCondition", back_populates="category")

class MedicalReference(Base):
    __tablename__ = "medical_references"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    authors = Column(String(255), nullable=True)
    journal_or_publisher = Column(String(200), nullable=True)
    publication_year = Column(Integer, nullable=True)
    doi_or_url = Column(String(300), nullable=True)
    guideline_body = Column(String(100), nullable=True)  # WHO, AUA, EAU, ASRM
    evidence_classification = Column(String(100), default=EvidenceClassification.GUIDELINE_CONSENSUS.value)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    conditions = relationship("MedicalCondition", secondary=condition_references, back_populates="references")

class MedicalCondition(Base):
    __tablename__ = "medical_conditions"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(120), unique=True, index=True, nullable=False)
    category_id = Column(Integer, ForeignKey("medical_categories.id"), nullable=False)
    organs_involved = Column(JSON, default=list)  # e.g. ["Testes", "Pampiniform Plexus", "Scrotum"]
    evidence_classification = Column(String(100), default="Level 1A")
    publication_status = Column(SQLEnum(PublicationStatus), default=PublicationStatus.DRAFT, nullable=False, index=True)
    current_version = Column(Integer, default=1, nullable=False)
    last_reviewed_at = Column(DateTime, nullable=True)
    clinical_reviewer = Column(String(150), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    category = relationship("MedicalCategory", back_populates="conditions")
    contents = relationship("ConditionContent", back_populates="condition", cascade="all, delete-orphan")
    references = relationship("MedicalReference", secondary=condition_references, back_populates="conditions")
    versions = relationship("ContentVersion", back_populates="condition", cascade="all, delete-orphan", order_by="desc(ContentVersion.version_number)")
    review_records = relationship("ClinicalReviewRecord", back_populates="condition", cascade="all, delete-orphan", order_by="desc(ClinicalReviewRecord.created_at)")

class ConditionContent(Base):
    """Bilingual translated content fields for a condition (en / ar)"""
    __tablename__ = "condition_contents"

    id = Column(Integer, primary_key=True, index=True)
    condition_id = Column(Integer, ForeignKey("medical_conditions.id", ondelete="CASCADE"), nullable=False)
    language = Column(String(10), nullable=False, index=True)  # 'en' or 'ar'
    
    # 20 Structured Fields Components
    name = Column(String(200), nullable=False)
    short_description = Column(String(500), nullable=False)
    detailed_explanation = Column(Text, nullable=False)
    biological_mechanism = Column(Text, nullable=False)  # Pathophysiology & biological mechanism
    causes_and_risk_factors = Column(Text, nullable=False)
    possible_symptoms = Column(Text, nullable=False)
    silent_asymptomatic_presentation = Column(Text, nullable=False)  # Silent / asymptomatic alerts
    clinical_significance = Column(Text, nullable=False)  # Impact on fertility & overall health
    diagnostic_investigations = Column(Text, nullable=False)  # Semen analysis, ultrasound, endocrine workup
    clinical_next_steps = Column(Text, nullable=False)  # Navigation pathways & specialist guidance

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    condition = relationship("MedicalCondition", back_populates="contents")

class ContentVersion(Base):
    """Historical audit snapshot of a condition's full state for version tracking & rollbacks"""
    __tablename__ = "content_versions"

    id = Column(Integer, primary_key=True, index=True)
    condition_id = Column(Integer, ForeignKey("medical_conditions.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    snapshot_data = Column(JSON, nullable=False)  # Complete JSON snapshot of condition, translations & references
    change_summary = Column(String(500), nullable=True)
    created_by = Column(String(150), default="System")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    condition = relationship("MedicalCondition", back_populates="versions")

class ClinicalReviewRecord(Base):
    """Audit log of clinical reviews, approvals, rejections, and reviewer rationales"""
    __tablename__ = "clinical_review_records"

    id = Column(Integer, primary_key=True, index=True)
    condition_id = Column(Integer, ForeignKey("medical_conditions.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    reviewer_name = Column(String(150), nullable=False)
    reviewer_role = Column(String(150), nullable=False)  # e.g., "Consultant Andrologist / UAE MOHAP Registered"
    action = Column(String(50), nullable=False)  # SUBMIT_FOR_REVIEW, APPROVE, REJECT, PUBLISH, ARCHIVE
    notes = Column(Text, nullable=True)  # Reviewer comments, clinical feedback, required modifications
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    condition = relationship("MedicalCondition", back_populates="review_records")
