import pytest
from app.core.database import Base
from app.models.facility import HealthcareFacility
import sqlite3

EXPECTED_17_TABLES = {
    'users', 'medical_categories', 'medical_references', 'audit_logs',
    'questionnaire_versions', 'clinical_rules', 'medical_conditions', 'questions',
    'assessments', 'clinical_rule_versions', 'condition_references', 'condition_contents',
    'content_versions', 'clinical_review_records', 'assessment_responses',
    'assessment_reports', 'healthcare_facilities'
}

def test_all_17_metadata_tables_registered():
    """Verify all 17 tables are registered with SQLAlchemy Base.metadata."""
    metadata_tables = set(Base.metadata.tables.keys())
    assert len(metadata_tables) == 17, f"Expected 17 tables in metadata, got {len(metadata_tables)}: {metadata_tables}"
    assert metadata_tables == EXPECTED_17_TABLES, f"Table set mismatch: {EXPECTED_17_TABLES ^ metadata_tables}"
    assert 'healthcare_facilities' in metadata_tables

def test_healthcare_facility_physical_parity():
    """Verify HealthcareFacility model matches physical table columns and indexes."""
    from app.core.config import settings
    
    # Check physical SQLite table in genovex.db
    conn = sqlite3.connect(settings.DATABASE_URL.replace("sqlite:///", ""))
    cursor = conn.cursor()
    
    # 1. Column counts and names
    cursor.execute("PRAGMA table_info(healthcare_facilities);")
    physical_cols = {r[1]: r[2] for r in cursor.fetchall()}
    assert len(physical_cols) == 27, f"Expected 27 columns, found {len(physical_cols)}"
    
    orm_cols = {c.name: str(c.type) for c in HealthcareFacility.__table__.columns}
    assert len(orm_cols) == 27, f"Expected 27 ORM columns, found {len(orm_cols)}"
    assert set(physical_cols.keys()) == set(orm_cols.keys()), "Column names do not match between physical and ORM"
    
    # 2. Indexes count
    cursor.execute("PRAGMA index_list(healthcare_facilities);")
    physical_indexes = [r[1] for r in cursor.fetchall()]
    assert len(physical_indexes) == 6, f"Expected 6 indexes on healthcare_facilities, found {len(physical_indexes)}"
    
    # 3. Existing 8 records preserved
    cursor.execute("SELECT COUNT(*) FROM healthcare_facilities;")
    count = cursor.fetchone()[0]
    assert count == 8, f"Expected 8 healthcare facilities, found {count}"
    
    conn.close()

if __name__ == "__main__":
    test_all_17_metadata_tables_registered()
    test_healthcare_facility_physical_parity()
    print("ALL SCHEMA PARITY TESTS PASSED (Exit Code 0)")
