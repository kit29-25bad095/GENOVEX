from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.clinical_rules import ClinicalOutcomeTier

class AssessmentReport(Base):
    """
    Compiled Evidence-Linked Assessment Report.
    Stores an immutable historical snapshot of the questionnaire responses,
    triggered clinical rules, evidence references, and non-diagnostic explanations.
    Guarantees 100% reproducibility even if clinical rules or questionnaires are updated later.
    """
    __tablename__ = "assessment_reports"

    id = Column(Integer, primary_key=True, index=True)
    report_reference = Column(String(64), unique=True, index=True, nullable=False)  # e.g., "GNX-RPT-2026-F98B2A"
    assessment_id = Column(Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    session_token = Column(String(100), index=True, nullable=False)

    # Engine & Questionnaire Version Pinned Identifiers
    questionnaire_version_tag = Column(String(50), nullable=False)  # e.g., "v1.0.0"
    rule_engine_version = Column(String(50), default="v1.0.0", nullable=False)

    # Four Assessment Outcome Tiers
    outcome_tier = Column(SQLEnum(ClinicalOutcomeTier), nullable=False, index=True)
    outcome_title_en = Column(String(250), nullable=False)
    outcome_title_ar = Column(String(250), nullable=False)
    outcome_description_en = Column(Text, nullable=False)
    outcome_description_ar = Column(Text, nullable=False)

    # Urgent Red Flag Pathway
    is_urgent_red_flag = Column(Boolean, default=False, index=True)
    urgent_emergency_guidance_en = Column(Text, nullable=True)
    urgent_emergency_guidance_ar = Column(Text, nullable=True)

    # Clinical Navigation Specialties & Next Steps
    recommended_specialties = Column(JSON, default=list, nullable=False)  # e.g. ["Male Reproductive Urologist / Andrologist"]
    recommended_next_steps_en = Column(JSON, default=list, nullable=False)
    recommended_next_steps_ar = Column(JSON, default=list, nullable=False)

    # Structured Clinical Snapshots
    identified_risk_factors_json = Column(JSON, default=list, nullable=False)
    triggered_rules_snapshot_json = Column(JSON, default=list, nullable=False)
    responses_summary_json = Column(JSON, default=list, nullable=False)
    evidence_citations_json = Column(JSON, default=list, nullable=False)

    # Non-Diagnostic Legal & Clinical Disclaimers
    clinical_disclaimer_en = Column(Text, nullable=False)
    clinical_disclaimer_ar = Column(Text, nullable=False)

    is_locked = Column(Boolean, default=True, nullable=False)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    assessment = relationship("Assessment")
