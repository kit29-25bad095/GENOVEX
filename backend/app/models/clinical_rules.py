from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, Enum as SQLEnum
from app.core.database import Base

class ClinicalOutcomeTier(str, enum.Enum):
    TIER_1_NO_RISK = "NO_RISK_FACTORS_REPORTED"
    TIER_2_RISK_FACTORS = "RISK_FACTORS_IDENTIFIED"
    TIER_3_EVAL_RECOMMENDED = "CLINICAL_EVALUATION_RECOMMENDED"
    TIER_4_URGENT = "URGENT_MEDICAL_ASSESSMENT"

class ClinicalRuleStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"

class ClinicalRule(Base):
    """
    CRITICAL ARCHITECTURAL BOUNDARY:
    This model governs the deterministic clinical assessment engine.
    It is STRICTLY DECOUPLED from educational medical content (`MedicalCondition`).
    Editing educational copy does NOT alter clinical assessment triage or scoring.
    """
    __tablename__ = "clinical_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_code = Column(String(50), unique=True, index=True, nullable=False)  # e.g., "R-VAR-01", "R-URG-TEST-TORSION"
    name = Column(String(200), nullable=False)
    target_condition_slug = Column(String(120), nullable=True)  # Read-only reference tag, not a foreign key cascade
    
    # Priority & Outcome
    outcome_tier = Column(SQLEnum(ClinicalOutcomeTier), nullable=False)
    is_urgent_red_flag = Column(Boolean, default=False, index=True)
    priority_rank = Column(Integer, default=100)  # Lower number = higher evaluation precedence
    
    # Logic Specification (Deterministic JSON predicate tree)
    trigger_criteria = Column(JSON, nullable=False)
    
    # Clinical Rationale & Guidelines
    clinical_rationale_en = Column(Text, nullable=False)
    clinical_rationale_ar = Column(Text, nullable=False)
    guideline_source = Column(String(150), nullable=False)  # e.g. "EAU Male Infertility Guidelines 2024"
    evidence_level = Column(String(50), default="Level 1A")
    
    # Independent Versioning & Approval
    rule_version = Column(String(20), default="1.0.0", nullable=False)
    status = Column(SQLEnum(ClinicalRuleStatus), default=ClinicalRuleStatus.DRAFT, nullable=False)
    approved_by = Column(String(150), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
