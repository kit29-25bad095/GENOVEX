"""
Comprehensive 17-Table Schema Parity Verification Script.
Compares physical SQLite tables and columns against SQLAlchemy Base.metadata.
"""

import sys
from pathlib import Path
from sqlalchemy import create_engine, inspect

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import Base
# Ensure all models are imported and registered
import app.models.medical_content
import app.models.clinical_rules
import app.models.questionnaire
import app.models.assessment_report
import app.models.facility
import app.core.security

EXPECTED_17_TABLES = {
    "healthcare_facilities",
    "medical_categories",
    "medical_references",
    "users",
    "audit_logs",
    "clinical_rules",
    "medical_conditions",
    "questionnaire_versions",
    "assessments",
    "clinical_review_records",
    "clinical_rule_versions",
    "condition_contents",
    "condition_references",
    "content_versions",
    "questions",
    "assessment_reports",
    "assessment_responses",
}

def verify_schema_parity(db_path: str):
    print(f"Verifying schema parity for: {db_path}")
    engine = create_engine(f"sqlite:///{db_path}")
    insp = inspect(engine)

    db_tables = set(insp.get_table_names())
    meta_tables = set(Base.metadata.tables.keys())

    print(f"Physical tables in database ({len(db_tables)}): {sorted(list(db_tables))}")
    print(f"Metadata tables defined ({len(meta_tables)}): {sorted(list(meta_tables))}")

    # Verify all 17 tables exist in both
    for t in EXPECTED_17_TABLES:
        assert t in db_tables, f"Table missing from physical database: {t}"
        assert t in meta_tables, f"Table missing from Base.metadata: {t}"

    print("All 17 application tables verified present.")

    # Check columns for each table
    mismatches = []
    for table_name in sorted(EXPECTED_17_TABLES):
        physical_cols = {col["name"]: col for col in insp.get_columns(table_name)}
        meta_table = Base.metadata.tables[table_name]
        meta_col_names = set(meta_table.columns.keys())
        phys_col_names = set(physical_cols.keys())

        if meta_col_names != phys_col_names:
            diff = meta_col_names ^ phys_col_names
            mismatches.append(f"Column name difference in table {table_name}: {diff}")

    if mismatches:
        print("Schema parity discrepancies found:")
        for m in mismatches:
            print(f" - {m}")
        sys.exit(1)

    print("100% Column Parity Verified across all 17 tables!")

    # Check foreign keys
    for table_name in sorted(EXPECTED_17_TABLES):
        fks = insp.get_foreign_keys(table_name)
        meta_fks = Base.metadata.tables[table_name].foreign_keys
        print(f"Table {table_name:25s}: {len(physical_cols)} cols, {len(fks)} physical FKs, {len(meta_fks)} metadata FKs")

    engine.dispose()
    return True

if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "genovex.db"
    verify_schema_parity(db_path)
