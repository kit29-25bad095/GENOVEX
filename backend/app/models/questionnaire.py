from datetime import datetime, timezone
import enum
import uuid
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, 
    Table, JSON, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from app.core.database import Base

class QuestionnaireStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"

class QuestionDomain(str, enum.Enum):
    BASIC_HEALTH = "BASIC_HEALTH"                           # Domain 1
    REPRODUCTIVE_HISTORY = "REPRODUCTIVE_HISTORY"           # Domain 2
    TESTICULAR_HISTORY = "TESTICULAR_HISTORY"               # Domain 3
    MEDICAL_HISTORY = "MEDICAL_HISTORY"                     # Domain 4
    HORMONAL_HEALTH = "HORMONAL_HEALTH"                     # Domain 5
    METABOLIC_HEALTH = "METABOLIC_HEALTH"                   # Domain 6
    LIFESTYLE_HABITS = "LIFESTYLE_HABITS"                   # Domain 7
    MEDICATION_SUBSTANCE = "MEDICATION_SUBSTANCE"           # Domain 8
    OCCUPATIONAL_EXPOSURE = "OCCUPATIONAL_EXPOSURE"         # Domain 9
    SEXUAL_EJACULATORY = "SEXUAL_EJACULATORY"               # Domain 10
    FAMILY_GENETIC = "FAMILY_GENETIC"                       # Domain 11

class QuestionType(str, enum.Enum):
    YES_NO = "YES_NO"
    SINGLE_CHOICE = "SINGLE_CHOICE"
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE"
    NUMERIC = "NUMERIC"
    DURATION_MONTHS = "DURATION_MONTHS"
    FREE_TEXT = "FREE_TEXT"

class AssessmentStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    REVIEW_READY = "REVIEW_READY"
    SUBMITTED = "SUBMITTED"
    LOCKED = "LOCKED"

class QuestionnaireVersion(Base):
    __tablename__ = "questionnaire_versions"

    id = Column(Integer, primary_key=True, index=True)
    version_tag = Column(String(50), unique=True, index=True, nullable=False) # e.g. "v1.0.0"
    title_en = Column(String(200), nullable=False)
    title_ar = Column(String(200), nullable=False)
    status = Column(SQLEnum(QuestionnaireStatus), default=QuestionnaireStatus.DRAFT, nullable=False, index=True)
    published_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True)
    clinical_reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    clinical_reviewer_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    questions = relationship("Question", back_populates="version", cascade="all, delete-orphan", order_by="Question.display_order")
    assessments = relationship("Assessment", back_populates="questionnaire_version")
    reviewer = relationship("User", foreign_keys=[clinical_reviewer_id])

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    version_id = Column(Integer, ForeignKey("questionnaire_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    domain_code = Column(SQLEnum(QuestionDomain), nullable=False, index=True)
    question_key = Column(String(100), nullable=False, index=True) # e.g. "Q_TESTIS_SURGERY"
    
    # Bilingual Text
    text_en = Column(Text, nullable=False)
    text_ar = Column(Text, nullable=False)
    help_text_en = Column(Text, nullable=True)
    help_text_ar = Column(Text, nullable=True)
    
    question_type = Column(SQLEnum(QuestionType), nullable=False)
    options_json = Column(JSON, default=list) # List of {key, label_en, label_ar, order}
    
    is_required = Column(Boolean, default=True)
    allows_unsure = Column(Boolean, default=True) # "Unsure" is never treated as negative
    allows_prefer_not_to_say = Column(Boolean, default=True)
    
    # Clinical Rationale & Guidelines
    clinical_rationale_en = Column(Text, nullable=False)
    clinical_rationale_ar = Column(Text, nullable=False)
    evidence_references = Column(JSON, default=list) # e.g. ["EAU Male Infertility Guidelines 2024", "WHO 6th Ed"]
    
    display_order = Column(Integer, default=0)
    is_urgent_red_flag = Column(Boolean, default=False, index=True) # Immediate acute danger warning
    
    # Adaptive Conditional Logic
    conditional_parent_key = Column(String(100), nullable=True) # Parent question key this question depends on
    conditional_trigger_values = Column(JSON, nullable=True)    # Values of parent that reveal this question, e.g. ["yes"]
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    version = relationship("QuestionnaireVersion", back_populates="questions")
    responses = relationship("AssessmentResponse", back_populates="question")

class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    session_token = Column(String(100), unique=True, index=True, nullable=False)
    
    # CRITICAL VERSION PINNING: Assessment stays locked to this questionnaire version
    questionnaire_version_id = Column(Integer, ForeignKey("questionnaire_versions.id"), nullable=False)
    status = Column(SQLEnum(AssessmentStatus), default=AssessmentStatus.IN_PROGRESS, nullable=False, index=True)
    
    current_domain_index = Column(Integer, default=0) # 0 to 10
    total_domains = Column(Integer, default=11)
    
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_saved_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    submitted_at = Column(DateTime, nullable=True)

    questionnaire_version = relationship("QuestionnaireVersion", back_populates="assessments")
    responses = relationship("AssessmentResponse", back_populates="assessment", cascade="all, delete-orphan")
    user = relationship("User", foreign_keys=[user_id])

class AssessmentResponse(Base):
    __tablename__ = "assessment_responses"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(String(36), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    question_key = Column(String(100), nullable=False)
    
    # Answer Storage
    answer_value = Column(JSON, nullable=True) # String, list, number, etc.
    is_unsure = Column(Boolean, default=False)
    is_prefer_not_to_say = Column(Boolean, default=False)
    
    conditional_pathway_active = Column(Boolean, default=True) # Was this question visible to user?
    response_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    assessment = relationship("Assessment", back_populates="responses")
    question = relationship("Question", back_populates="responses")
