from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.models.medical_content import MedicalCondition, PublicationStatus
from app.models.clinical_rules import ClinicalRule, ClinicalRuleStatus
from app.models.questionnaire import QuestionnaireVersion, QuestionnaireStatus

class ClinicalAssetMaintenanceService:
    """
    Service for ongoing maintenance, review tracking, and staleness detection
    across Medical Content, Clinical Rules, and Adaptive Questionnaires.
    Ensures clinical assets stay synchronized with current international guidelines (EAU, AUA, WHO).
    """

    REVIEW_VALIDITY_DAYS = 365  # Clinical guidelines recommend annual review

    @classmethod
    def get_maintenance_overview(cls, db: Session) -> Dict[str, Any]:
        """Provides an operational summary of all clinical assets and overdue review items."""
        now = datetime.now(timezone.utc)
        stale_threshold = now - timedelta(days=cls.REVIEW_VALIDITY_DAYS)

        # 1. Medical Content Review Status
        all_conditions = db.query(MedicalCondition).all()
        published_conditions = [c for c in all_conditions if c.publication_status == PublicationStatus.PUBLISHED]
        stale_conditions = [
            c for c in published_conditions 
            if c.last_reviewed_at is None or c.last_reviewed_at.replace(tzinfo=timezone.utc if c.last_reviewed_at.tzinfo is None else None) < stale_threshold
        ]

        # 2. Clinical Rules Review Status
        all_rules = db.query(ClinicalRule).all()
        published_rules = [r for r in all_rules if r.status == ClinicalRuleStatus.PUBLISHED]
        stale_rules = [
            r for r in published_rules 
            if r.approved_at is None or r.approved_at.replace(tzinfo=timezone.utc if r.approved_at.tzinfo is None else None) < stale_threshold
        ]

        # 3. Questionnaire Versions
        all_questionnaires = db.query(QuestionnaireVersion).all()
        active_questionnaire = db.query(QuestionnaireVersion).filter(QuestionnaireVersion.status == QuestionnaireStatus.PUBLISHED).first()

        return {
            "timestamp": now.isoformat(),
            "review_validity_period_days": cls.REVIEW_VALIDITY_DAYS,
            "medical_conditions": {
                "total_count": len(all_conditions),
                "published_count": len(published_conditions),
                "stale_review_count": len(stale_conditions),
                "stale_condition_slugs": [c.slug for c in stale_conditions]
            },
            "clinical_rules": {
                "total_count": len(all_rules),
                "published_count": len(published_rules),
                "stale_review_count": len(stale_rules),
                "stale_rule_codes": [r.rule_code for r in stale_rules]
            },
            "questionnaires": {
                "total_versions": len(all_questionnaires),
                "active_version": active_questionnaire.version_tag if active_questionnaire else None,
                "active_published_at": active_questionnaire.published_at.isoformat() if active_questionnaire and active_questionnaire.published_at else None
            }
        }
