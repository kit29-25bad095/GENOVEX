import os
import shutil
import sqlite3
import hashlib
import pytest

from app.core.config import AUTHORITATIVE_DB_PATH
from scripts.reconstruct_assessment_reports import execute_reconstruction, EXPECTED_7_INDEXES

TIER1_BACKUP_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "backups",
    "genovex_backup_tier1_20261120_020738.db"
)
TIER1_BACKUP_SHA256 = "ac10a688bd070ab0f4d90e77c5055714e634c8aed51f68c02e12909fe3ef5a09"

SANDBOX_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "backups",
    "sandbox"
)

EXPECTED_COUNTS = {
    'users': 4,
    'medical_categories': 5,
    'medical_references': 3,
    'audit_logs': 0,
    'questionnaire_versions': 1,
    'clinical_rules': 22,
    'medical_conditions': 5,
    'questions': 19,
    'assessments': 87,
    'clinical_rule_versions': 22,
    'condition_references': 10,
    'condition_contents': 10,
    'content_versions': 6,
    'clinical_review_records': 0,
    'assessment_responses': 178,
    'assessment_reports': 86,
    'healthcare_facilities': 8
}

def get_file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().lower()

def test_stage4_disposable_sandbox_reconstruction():
    """
    Stage 4: Execute and verify 14-step reconstruction on disposable_test.db in sandbox.
    Verifies assessment_id column converted to VARCHAR(36), exactly 86 rows preserved,
    all 7 exact indexes present, zero FK violations, and integrity check ok.
    """
    os.makedirs(SANDBOX_DIR, exist_ok=True)
    disposable_db = os.path.join(SANDBOX_DIR, "disposable_test.db")

    # 1. Stage fresh copy from Tier 1 backup
    shutil.copyfile(TIER1_BACKUP_PATH, disposable_db)
    assert os.path.exists(disposable_db)

    # 2. Execute 14-step reconstruction procedure
    success = execute_reconstruction(disposable_db)
    assert success is True

    # 3. Independent verification of reconstructed database
    conn = sqlite3.connect(disposable_db)
    cur = conn.cursor()

    # Column type check: VARCHAR(36)
    cur.execute("PRAGMA table_info(assessment_reports);")
    cols = {r[1]: r[2] for r in cur.fetchall()}
    assert cols["assessment_id"] == "VARCHAR(36)", f"Expected VARCHAR(36), got {cols['assessment_id']}"

    # Row count: 86
    cur.execute("SELECT COUNT(*) FROM assessment_reports;")
    count = cur.fetchone()[0]
    assert count == 86, f"Expected 86 rows, got {count}"

    # Foreign key check: 0 violations
    cur.execute("PRAGMA foreign_key_check;")
    fk_violations = cur.fetchall()
    assert len(fk_violations) == 0, f"FK violations: {fk_violations}"

    # Integrity check: ok
    cur.execute("PRAGMA integrity_check;")
    integrity = cur.fetchone()[0]
    assert integrity == "ok"

    # Indexes check: all 7 exact indexes
    cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='assessment_reports';")
    indexes = {r[0] for r in cur.fetchall()}
    assert indexes == EXPECTED_7_INDEXES

    # 17 tables parity
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = {r[0] for r in cur.fetchall()}
    assert len(tables) == 17

    for tbl, expected_cnt in EXPECTED_COUNTS.items():
        cur.execute(f"SELECT COUNT(*) FROM {tbl};")
        actual_cnt = cur.fetchone()[0]
        assert actual_cnt == expected_cnt, f"Table {tbl} count mismatch: expected {expected_cnt}, got {actual_cnt}"

    conn.close()

def test_stage4_disaster_recovery_simulation():
    """
    Stage 4: Disaster Recovery Verification.
    Simulate catastrophic failure on a disposable test database,
    execute recovery from Tier 1 backup, and verify complete restoration.
    """
    os.makedirs(SANDBOX_DIR, exist_ok=True)
    recovery_test_db = os.path.join(SANDBOX_DIR, "recovery_simulation.db")

    # 1. Create simulated corrupted file
    with open(recovery_test_db, "wb") as f:
        f.write(b"CORRUPTED_DATABASE_DATA_SIMULATION_HEADER")

    # 2. Execute Disaster Recovery Procedure from Tier 1 Backup
    # In recovery protocol: replace corrupted database with pristine Tier 1 atomic backup
    shutil.copyfile(TIER1_BACKUP_PATH, recovery_test_db)

    # 3. Verify recovered database
    conn = sqlite3.connect(recovery_test_db)
    cur = conn.cursor()

    cur.execute("PRAGMA integrity_check;")
    assert cur.fetchone()[0] == "ok"

    cur.execute("PRAGMA foreign_key_check;")
    assert len(cur.fetchall()) == 0

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = {r[0] for r in cur.fetchall()}
    assert len(tables) == 17

    for tbl, expected_cnt in EXPECTED_COUNTS.items():
        cur.execute(f"SELECT COUNT(*) FROM {tbl};")
        assert cur.fetchone()[0] == expected_cnt

    conn.close()

    # Confirm restored file hash matches Tier 1 backup SHA-256
    restored_hash = get_file_sha256(recovery_test_db)
    assert restored_hash == TIER1_BACKUP_SHA256

    # Cleanup temporary simulation file
    if os.path.exists(recovery_test_db):
        os.remove(recovery_test_db)

def test_stage4_live_database_remains_untouched():
    """
    Stage 4 / Stage 6 Verification: Confirm pre-reconstruction backups remain intact,
    and live database has successfully migrated assessment_id to VARCHAR(36).
    """
    assert os.path.exists(TIER1_BACKUP_PATH), "Tier 1 backup missing"
    t1_hash = get_file_sha256(TIER1_BACKUP_PATH)
    assert t1_hash == TIER1_BACKUP_SHA256, f"Tier 1 backup modified! {t1_hash} vs {TIER1_BACKUP_SHA256}"

    # Verify column in Tier 1 backup is INTEGER
    conn_t1 = sqlite3.connect(TIER1_BACKUP_PATH)
    cur_t1 = conn_t1.cursor()
    cur_t1.execute("PRAGMA table_info(assessment_reports);")
    cols_t1 = {r[1]: r[2] for r in cur_t1.fetchall()}
    conn_t1.close()
    assert cols_t1["assessment_id"] == "INTEGER", "Tier 1 backup must preserve INTEGER assessment_id"

    # Verify live database has successfully migrated to VARCHAR(36)
    conn_live = sqlite3.connect(str(AUTHORITATIVE_DB_PATH))
    cur_live = conn_live.cursor()
    cur_live.execute("PRAGMA table_info(assessment_reports);")
    cols_live = {r[1]: r[2] for r in cur_live.fetchall()}
    conn_live.close()
    assert cols_live["assessment_id"] == "VARCHAR(36)", f"Expected VARCHAR(36) in live DB, got {cols_live['assessment_id']}"
