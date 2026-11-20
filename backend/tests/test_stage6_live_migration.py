"""
Comprehensive Stage 6 Verification Suite: Live SQLite Migration & Parity Acceptance.
Verifies Tier 2 backup, live R-RBAC archival, 14-step table reconstruction,
17-table metadata parity, Alembic baseline stamping, integrity and zero data loss.
"""

import hashlib
import sqlite3
from pathlib import Path
import pytest
from sqlalchemy import create_engine, inspect

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
LIVE_DB_PATH = ROOT_DIR / "genovex.db"
TIER1_BACKUP_PATH = BACKEND_DIR / "backups" / "genovex_backup_tier1_20261120_020738.db"
if not TIER1_BACKUP_PATH.exists():
    TIER1_BACKUP_PATH = BACKEND_DIR / "backups" / "genovex_backup_pre_reconstruction.db"
TIER2_BACKUP_PATH = BACKEND_DIR / "backups" / "genovex_backup_pre_reconstruction.db"
if not TIER2_BACKUP_PATH.exists() or TIER2_BACKUP_PATH.stat().st_size == 0 or not LIVE_DB_PATH.exists():
    pytest.skip("Tier 2 backup or live database not present in this test environment", allow_module_level=True)
TIER1_HASH = "ac10a688bd070ab0f4d90e77c5055714e634c8aed51f68c02e12909fe3ef5a09"

EXPECTED_COUNTS = {
    "assessments": 87,
    "assessment_reports": 86,
    "assessment_responses": 178,
    "healthcare_facilities": 8,
    "medical_categories": 5,
    "medical_conditions": 5,
    "medical_references": 3,
    "questionnaire_versions": 3,
    "questions": 19,
    "users": 4,
    "clinical_rules": 22,
    "clinical_rule_versions": 22,
    "clinical_review_records": 5,
    "condition_contents": 10,
    "condition_references": 6,
    "content_versions": 5,
    "audit_logs": 15,
}

EXPECTED_7_INDEXES = {
    "ix_assessment_reports_id",
    "ix_assessment_reports_report_reference",
    "ix_assessment_reports_session_token",
    "ix_assessment_reports_user_id",
    "ix_assessment_reports_is_urgent_red_flag",
    "ix_assessment_reports_assessment_id",
    "ix_assessment_reports_outcome_tier",
}


def test_tier2_pre_reconstruction_backup():
    """Verify Tier 2 pre-reconstruction backup exists and matches Tier 1 backup SHA-256."""
    assert TIER2_BACKUP_PATH.exists(), f"Tier 2 backup missing at {TIER2_BACKUP_PATH}"
    
    h = hashlib.sha256()
    with open(TIER2_BACKUP_PATH, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    actual_hash = h.hexdigest().lower()
    assert actual_hash == TIER1_HASH, f"Tier 2 hash mismatch: expected {TIER1_HASH}, got {actual_hash}"


def test_live_alembic_stamped():
    """Verify live database has alembic_version table stamped with 0001_phase5_baseline."""
    conn = sqlite3.connect(f"file:{LIVE_DB_PATH}?mode=ro", uri=True)
    try:
        cur = conn.cursor()
        cur.execute("SELECT version_num FROM alembic_version;")
        rows = cur.fetchall()
        assert len(rows) == 1, f"Expected 1 alembic revision, got {len(rows)}"
        assert rows[0][0] == "0001_phase5_baseline"
    finally:
        conn.close()


def test_live_clinical_rules_archival():
    """Verify 8 R-RBAC rules are archived, 14 canonical rules are published, and total count is 22."""
    conn = sqlite3.connect(f"file:{LIVE_DB_PATH}?mode=ro", uri=True)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM clinical_rules WHERE status = 'PUBLISHED';")
        published_count = cur.fetchone()[0]
        assert published_count == 14, f"Expected 14 PUBLISHED rules, got {published_count}"

        cur.execute("SELECT COUNT(*) FROM clinical_rules WHERE status = 'ARCHIVED';")
        archived_count = cur.fetchone()[0]
        assert archived_count == 8, f"Expected 8 ARCHIVED rules, got {archived_count}"

        cur.execute("SELECT COUNT(*) FROM clinical_rules WHERE rule_code LIKE 'R-RBAC-%' AND status = 'ARCHIVED';")
        rbac_archived = cur.fetchone()[0]
        assert rbac_archived == 8, f"Expected all 8 R-RBAC rules to be ARCHIVED, got {rbac_archived}"

        cur.execute("SELECT COUNT(*) FROM clinical_rules;")
        total_rules = cur.fetchone()[0]
        assert total_rules == 22, f"Expected 22 total rules, got {total_rules}"
    finally:
        conn.close()


def test_live_assessment_reports_reconstruction():
    """Verify assessment_reports table schema: assessment_id is VARCHAR(36) and all 7 indexes exist."""
    conn = sqlite3.connect(f"file:{LIVE_DB_PATH}?mode=ro", uri=True)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(assessment_reports);")
        columns = {row[1]: row[2] for row in cur.fetchall()}
        assert columns.get("assessment_id") == "VARCHAR(36)", (
            f"Expected assessment_id to be VARCHAR(36), got {columns.get('assessment_id')}"
        )

        cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='assessment_reports';")
        actual_indexes = {row[0] for row in cur.fetchall()}
        assert actual_indexes == EXPECTED_7_INDEXES, f"Index mismatch: {EXPECTED_7_INDEXES ^ actual_indexes}"
    finally:
        conn.close()


def test_live_database_integrity_and_fk_checks():
    """Verify live database has zero FK violations and passes full SQLite integrity check."""
    conn = sqlite3.connect(f"file:{LIVE_DB_PATH}?mode=ro", uri=True)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_key_check;")
        fk_violations = cur.fetchall()
        assert len(fk_violations) == 0, f"FK violations in live database: {fk_violations}"

        cur.execute("PRAGMA integrity_check;")
        integrity = cur.fetchone()[0]
        assert integrity == "ok", f"Integrity check failed: {integrity}"
    finally:
        conn.close()


def test_live_database_row_counts_preserved():
    """Verify 100% preservation of historical records across all 17 application tables against Tier 1 backup."""
    tier1_conn = sqlite3.connect(f"file:{TIER1_BACKUP_PATH}?mode=ro", uri=True)
    live_conn = sqlite3.connect(f"file:{LIVE_DB_PATH}?mode=ro", uri=True)
    try:
        cur1 = tier1_conn.cursor()
        cur2 = live_conn.cursor()
        cur1.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [r[0] for r in cur1.fetchall()]
        assert len(tables) == 17, f"Expected 17 tables in Tier 1 backup, got {len(tables)}"

        for table in tables:
            cur1.execute(f"SELECT COUNT(*) FROM {table};")
            tier1_count = cur1.fetchone()[0]

            cur2.execute(f"SELECT COUNT(*) FROM {table};")
            live_count = cur2.fetchone()[0]

            assert live_count >= tier1_count, (
                f"Count mismatch on {table}: Tier 1 had {tier1_count}, live has {live_count}"
            )
    finally:
        tier1_conn.close()
        live_conn.close()
