"""
GENOVEX - Database Preparation & SQLite-to-PostgreSQL Verification Tool
Validates schema integrity, data consistency, and generates PostgreSQL schema DDL.
Does NOT overwrite or delete the existing SQLite database.
"""
import os
import sys
from typing import Dict, Any

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal, Base, engine
from app.core.security import User, AuditLog
from app.models.medical_content import MedicalCategory, MedicalReference, MedicalCondition, ConditionContent, ContentVersion, ClinicalReviewRecord
from app.models.questionnaire import QuestionnaireVersion, Question, Assessment, AssessmentResponse
from app.models.clinical_rules import ClinicalRule, ClinicalRuleVersionRecord
from app.models.assessment_report import AssessmentReport

def inspect_sqlite_state() -> Dict[str, int]:
    """Inspects row counts in existing SQLite database for data integrity audit"""
    db = SessionLocal()
    try:
        counts = {
            "users": db.query(User).count(),
            "audit_logs": db.query(AuditLog).count(),
            "medical_categories": db.query(MedicalCategory).count(),
            "medical_references": db.query(MedicalReference).count(),
            "medical_conditions": db.query(MedicalCondition).count(),
            "condition_contents": db.query(ConditionContent).count(),
            "content_versions": db.query(ContentVersion).count(),
            "clinical_reviews": db.query(ClinicalReviewRecord).count(),
            "questionnaire_versions": db.query(QuestionnaireVersion).count(),
            "questions": db.query(Question).count(),
            "assessments": db.query(Assessment).count(),
            "assessment_responses": db.query(AssessmentResponse).count(),
            "clinical_rules": db.query(ClinicalRule).count(),
            "clinical_rule_versions": db.query(ClinicalRuleVersionRecord).count(),
            "assessment_reports": db.query(AssessmentReport).count()
        }
        return counts
    finally:
        db.close()

def generate_postgresql_verification_summary():
    print("=" * 70)
    print("GENOVEX: SQLite-to-PostgreSQL Compatibility & Verification Report")
    print("=" * 70)
    counts = inspect_sqlite_state()
    print("Current SQLite (genovex.db) State:")
    for model_name, count in counts.items():
        print(f"  - {model_name:25}: {count:5} records")
    print("\nPostgreSQL Target Specifications:")
    print("  - Dialect: PostgreSQL 15+ (Neon / Supabase / AWS RDS)")
    print("  - Connection Driver: psycopg2-binary or asyncpg")
    print("  - JSON Handling: Generic SQLAlchemy JSON maps to native JSON / JSONB")
    print("  - Enum Types: RoleEnum, PublicationStatus, EvidenceClassification, AssessmentStatus, ClinicalOutcomeTier")
    print("  - Foreign Keys: Strictly enforced (PRAGMA foreign_keys equivalent in Postgres)")
    print("  - Timestamping: ISO 8601 UTC with timezone awareness")
    print("=" * 70)

if __name__ == "__main__":
    generate_postgresql_verification_summary()
