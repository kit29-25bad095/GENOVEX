"""
Deterministic 14-Step SQLite Table Reconstruction Procedure for assessment_reports.
Converts assessment_reports.assessment_id from INTEGER to VARCHAR(36)
with Foreign Key constraint to assessments(id) ON DELETE CASCADE,
recreating all 7 physical indexes and asserting exact row count and zero FK violations.
"""

import sqlite3
import argparse

EXPECTED_ROW_COUNT = 86

CREATE_NEW_TABLE_SQL = """
CREATE TABLE assessment_reports_new (
	id INTEGER NOT NULL, 
	report_reference VARCHAR(64) NOT NULL, 
	assessment_id VARCHAR(36) NOT NULL, 
	user_id INTEGER, 
	session_token VARCHAR(100) NOT NULL, 
	questionnaire_version_tag VARCHAR(50) NOT NULL, 
	rule_engine_version VARCHAR(50) NOT NULL, 
	outcome_tier VARCHAR(23) NOT NULL, 
	outcome_title_en VARCHAR(250) NOT NULL, 
	outcome_title_ar VARCHAR(250) NOT NULL, 
	outcome_description_en TEXT NOT NULL, 
	outcome_description_ar TEXT NOT NULL, 
	is_urgent_red_flag BOOLEAN, 
	urgent_emergency_guidance_en TEXT, 
	urgent_emergency_guidance_ar TEXT, 
	recommended_specialties JSON NOT NULL, 
	recommended_next_steps_en JSON NOT NULL, 
	recommended_next_steps_ar JSON NOT NULL, 
	identified_risk_factors_json JSON NOT NULL, 
	triggered_rules_snapshot_json JSON NOT NULL, 
	responses_summary_json JSON NOT NULL, 
	evidence_citations_json JSON NOT NULL, 
	clinical_disclaimer_en TEXT NOT NULL, 
	clinical_disclaimer_ar TEXT NOT NULL, 
	is_locked BOOLEAN NOT NULL, 
	generated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(assessment_id) REFERENCES assessments (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
"""

COPY_DATA_SQL = """
INSERT INTO assessment_reports_new (
    id, report_reference, assessment_id, user_id, session_token, 
    questionnaire_version_tag, rule_engine_version, outcome_tier, 
    outcome_title_en, outcome_title_ar, outcome_description_en, 
    outcome_description_ar, is_urgent_red_flag, urgent_emergency_guidance_en, 
    urgent_emergency_guidance_ar, recommended_specialties, 
    recommended_next_steps_en, recommended_next_steps_ar, 
    identified_risk_factors_json, triggered_rules_snapshot_json, 
    responses_summary_json, evidence_citations_json, clinical_disclaimer_en, 
    clinical_disclaimer_ar, is_locked, generated_at
)
SELECT 
    id, report_reference, CAST(assessment_id AS TEXT), user_id, session_token, 
    questionnaire_version_tag, rule_engine_version, outcome_tier, 
    outcome_title_en, outcome_title_ar, outcome_description_en, 
    outcome_description_ar, is_urgent_red_flag, urgent_emergency_guidance_en, 
    urgent_emergency_guidance_ar, recommended_specialties, 
    recommended_next_steps_en, recommended_next_steps_ar, 
    identified_risk_factors_json, triggered_rules_snapshot_json, 
    responses_summary_json, evidence_citations_json, clinical_disclaimer_en, 
    clinical_disclaimer_ar, is_locked, generated_at
FROM assessment_reports;
"""

INDEXES_SQL = [
    "CREATE INDEX ix_assessment_reports_id ON assessment_reports (id);",
    "CREATE UNIQUE INDEX ix_assessment_reports_report_reference ON assessment_reports (report_reference);",
    "CREATE INDEX ix_assessment_reports_session_token ON assessment_reports (session_token);",
    "CREATE INDEX ix_assessment_reports_user_id ON assessment_reports (user_id);",
    "CREATE INDEX ix_assessment_reports_is_urgent_red_flag ON assessment_reports (is_urgent_red_flag);",
    "CREATE INDEX ix_assessment_reports_assessment_id ON assessment_reports (assessment_id);",
    "CREATE INDEX ix_assessment_reports_outcome_tier ON assessment_reports (outcome_tier);"
]

EXPECTED_7_INDEXES = {
    'ix_assessment_reports_id',
    'ix_assessment_reports_report_reference',
    'ix_assessment_reports_session_token',
    'ix_assessment_reports_user_id',
    'ix_assessment_reports_is_urgent_red_flag',
    'ix_assessment_reports_assessment_id',
    'ix_assessment_reports_outcome_tier'
}

def execute_reconstruction(db_path: str):
    print(f"Executing 14-Step Table Reconstruction on: {db_path}")
    conn = sqlite3.connect(db_path, isolation_level=None)
    cur = conn.cursor()

    try:
        # Step 1: Foreign keys OFF for reconstruction transaction
        cur.execute("PRAGMA foreign_keys = OFF;")

        # Step 2: Begin Transaction
        cur.execute("BEGIN TRANSACTION;")

        # Step 3: Verify initial row count
        cur.execute("SELECT COUNT(*) FROM assessment_reports;")
        initial_count = cur.fetchone()[0]
        print(f"Step 3: Initial assessment_reports count: {initial_count}")
        assert initial_count == EXPECTED_ROW_COUNT, f"Expected {EXPECTED_ROW_COUNT} rows, got {initial_count}"

        # Step 4: Create new table with VARCHAR(36) assessment_id
        cur.execute(CREATE_NEW_TABLE_SQL)

        # Step 5: Copy data with type cast
        cur.execute(COPY_DATA_SQL)

        # Step 6: Verify row count of new table
        cur.execute("SELECT COUNT(*) FROM assessment_reports_new;")
        new_count = cur.fetchone()[0]
        print(f"Step 6: assessment_reports_new count: {new_count}")
        assert new_count == initial_count, f"Row count mismatch! Before: {initial_count}, After: {new_count}"

        # Step 7: Drop old table
        cur.execute("DROP TABLE assessment_reports;")

        # Step 8: Rename new table
        cur.execute("ALTER TABLE assessment_reports_new RENAME TO assessment_reports;")

        # Step 9: Recreate all 7 indexes
        for idx_sql in INDEXES_SQL:
            cur.execute(idx_sql)

        # Verify all 7 indexes exist
        cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='assessment_reports';")
        actual_indexes = {row[0] for row in cur.fetchall()}
        print(f"Step 9 Verification: Actual indexes on assessment_reports: {actual_indexes}")
        assert actual_indexes == EXPECTED_7_INDEXES, f"Index mismatch! Difference: {EXPECTED_7_INDEXES ^ actual_indexes}"

        # Step 10: In-transaction foreign_key_check
        cur.execute("PRAGMA foreign_key_check;")
        fk_violations = cur.fetchall()
        print(f"Step 10: Pre-commit FK violations: {len(fk_violations)}")
        assert len(fk_violations) == 0, f"FK violations detected before commit: {fk_violations}"

        # Step 11: Commit transaction
        cur.execute("COMMIT;")
        print("Step 11: Committed reconstruction transaction.")

        # Step 12: Re-enable foreign keys
        cur.execute("PRAGMA foreign_keys = ON;")

        # Step 13: Post-commit integrity check
        cur.execute("PRAGMA integrity_check;")
        integrity = cur.fetchone()[0]
        print(f"Step 13: Integrity check: {integrity}")
        assert integrity == "ok", f"Integrity check failed: {integrity}"

        # Step 14: Post-commit foreign key check
        cur.execute("PRAGMA foreign_key_check;")
        post_fk = cur.fetchall()
        print(f"Step 14: Post-commit FK violations: {len(post_fk)}")
        assert len(post_fk) == 0, f"Post-commit FK violations detected: {post_fk}"

        # Column type verification: confirm assessment_id is VARCHAR(36)
        cur.execute("PRAGMA table_info(assessment_reports);")
        cols = {r[1]: r[2] for r in cur.fetchall()}
        print(f"Verified assessment_id column type: {cols.get('assessment_id')}")
        assert cols.get('assessment_id') == 'VARCHAR(36)', f"Expected VARCHAR(36), got {cols.get('assessment_id')}"

        print(f"14-Step Reconstruction SUCCESSFUL on {db_path} (Exit Code 0)")
        return True

    except Exception as e:
        print(f"ERROR during reconstruction: {e}")
        try:
            cur.execute("ROLLBACK;")
        except Exception:
            pass
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reconstruct assessment_reports table in SQLite")
    parser.add_argument("db_path", help="Path to SQLite database")
    args = parser.parse_args()
    execute_reconstruction(args.db_path)
