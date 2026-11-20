from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship

class ClinicalOutcomeTier(str, enum.Enum):
    TIER_1_NO_RISK = "NO_REPORTED_RISK_FACTORS"
    TIER_2_RISK_FACTORS = "RISK_FACTORS_IDENTIFIED"
    TIER_3_EVAL_RECOMMENDED = "CLINICAL_EVALUATION_RECOMMENDED"
    TIER_4_URGENT = "URGENT_MEDICAL_ASSESSMENT"

class ClinicalRuleStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED_FOR_REVIEW = "SUBMITTED_FOR_REVIEW"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    ACTIVE = "PUBLISHED"  # Backward compatibility alias
    ARCHIVED = "ARCHIVED"
    RETIRED = "RETIRED"

from app.core.database import Base
from app.models.questionnaire import QuestionDomain

class ClinicalRule(Base):
    """
    CRITICAL ARCHITECTURAL BOUNDARY:
    Governs the deterministic clinical assessment engine.
    STRICTLY DECOUPLED from educational medical content (`MedicalCondition`).
    Editing educational descriptions does NOT alter clinical assessment triage or scoring.
    All rules are independently versioned and require explicit clinician sign-off.
    """
    __tablename__ = "clinical_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_code = Column(String(50), unique=True, index=True, nullable=False)  # e.g., "R-URG-SCROTAL-PAIN", "R-REP-PROLONGED-TTC"
    title_en = Column(String(250), nullable=False)
    title_ar = Column(String(250), nullable=False)
    target_condition_slug = Column(String(120), nullable=True)  # Read-only reference tag, not a foreign key cascade
    
    # Relevant Domain and Questions
    domain_code = Column(SQLEnum(QuestionDomain), nullable=False, index=True, default=QuestionDomain.TESTICULAR_HISTORY)
    relevant_question_keys = Column(JSON, nullable=False, default=list)  # List of string question keys, e.g. ["Q_ACUTE_SCROTAL_PAIN"]
    
    # Priority & Outcome
    outcome_tier = Column(SQLEnum(ClinicalOutcomeTier), nullable=False, index=True)
    is_urgent_red_flag = Column(Boolean, default=False, index=True)
    priority_rank = Column(Integer, default=100)  # 1-10: Emergency, 20-50: Tier 3, 60-90: Tier 2, 100: Baseline
    recommended_specialty = Column(String(150), nullable=True)  # e.g. "Male Reproductive Urologist / Andrologist"
    
    # Logic Specification (Deterministic JSON predicate tree)
    trigger_criteria = Column(JSON, nullable=False)
    missing_response_handling = Column(String(50), default="NEVER_NEGATIVE", nullable=False)
    
    # Clinical Rationale & Guidelines
    clinical_rationale_en = Column(Text, nullable=False)
    clinical_rationale_ar = Column(Text, nullable=False)
    evidence_references = Column(JSON, nullable=False, default=list)  # List of structured reference objects
    evidence_classification = Column(String(50), default="Level 1a", nullable=False)

    def __init__(self, **kwargs):
        if "name" in kwargs:
            name_val = kwargs.pop("name")
            kwargs.setdefault("title_en", name_val)
            kwargs.setdefault("title_ar", name_val)
        if "guideline_source" in kwargs:
            source_val = kwargs.pop("guideline_source")
            kwargs.setdefault("evidence_references", [{"title": source_val, "guideline_body": source_val, "year": 2024}])
        if "domain_code" not in kwargs:
            kwargs["domain_code"] = QuestionDomain.TESTICULAR_HISTORY
        if "relevant_question_keys" not in kwargs:
            kwargs["relevant_question_keys"] = []
        if "evidence_references" not in kwargs:
            kwargs["evidence_references"] = []
        if "title_ar" not in kwargs and "title_en" in kwargs:
            kwargs["title_ar"] = kwargs["title_en"]
        super().__init__(**kwargs)
    
    # Independent Versioning & Approval
    rule_version = Column(String(20), default="1.0.0", nullable=False)
    status = Column(SQLEnum(ClinicalRuleStatus), default=ClinicalRuleStatus.DRAFT, nullable=False, index=True)
    
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    clinical_reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    clinical_reviewer_notes = Column(Text, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    versions = relationship("ClinicalRuleVersionRecord", back_populates="rule", cascade="all, delete-orphan")


class ClinicalRuleVersionRecord(Base):
    """
    Immutable audit history of clinical rule iterations.
    Preserves exact historical rules for full assessment reproducibility.
    """
    __tablename__ = "clinical_rule_versions"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("clinical_rules.id", ondelete="CASCADE"), nullable=False, index=True)
    version_tag = Column(String(20), nullable=False)
    rule_code = Column(String(50), nullable=False)
    title_en = Column(String(250), nullable=False)
    title_ar = Column(String(250), nullable=False)
    outcome_tier = Column(SQLEnum(ClinicalOutcomeTier), nullable=False)
    is_urgent_red_flag = Column(Boolean, default=False)
    trigger_criteria = Column(JSON, nullable=False)
    evidence_references = Column(JSON, nullable=False)
    snapshot_json = Column(JSON, nullable=False)  # Full serialized rule definition
    
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    rule = relationship("ClinicalRule", back_populates="versions")
