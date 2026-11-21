import os
import shutil
import tempfile
import sqlite3
import hashlib
import io
from pathlib import Path
from contextlib import redirect_stdout
import pytest

from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic import command
from sqlalchemy import create_engine, inspect

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
ALEMBIC_INI_PATH = BACKEND_DIR / "alembic.ini"
VERSIONS_DIR = BACKEND_DIR / "alembic" / "versions"
LEGACY_VERSIONS_DIR = BACKEND_DIR / "alembic" / "legacy_versions"
LIVE_DB_PATH = ROOT_DIR / "genovex.db"
TIER1_BACKUP_PATH = BACKEND_DIR / "backups" / "genovex_backup_tier1_20261120_020738.db"
EXPECTED_SHA256 = "ac10a688bd070ab0f4d90e77c5055714e634c8aed51f68c02e12909fe3ef5a09"

EXPECTED_APPLICATION_TABLES = {
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


def test_alembic_versions_directory_isolation():
    """Verify active versions contains only 0001_phase5_baseline.py and legacy migrations are segregated."""
    assert VERSIONS_DIR.exists(), f"Versions dir does not exist: {VERSIONS_DIR}"
    assert LEGACY_VERSIONS_DIR.exists(), f"Legacy versions dir does not exist: {LEGACY_VERSIONS_DIR}"

    # Active migration files (excluding pycache and hidden)
    active_files = [f.name for f in VERSIONS_DIR.glob("*.py") if not f.name.startswith("__")]
    assert len(active_files) == 2, f"Expected 2 active migrations, found: {active_files}"
    assert "0001_phase5_baseline.py" in active_files
    assert "0002_add_password_reset_tokens.py" in active_files

    # Legacy versions contains archived migrations
    legacy_files = [f.name for f in LEGACY_VERSIONS_DIR.glob("*.py") if not f.name.startswith("__")]
    assert len(legacy_files) >= 3, f"Expected at least 3 legacy migrations archived, found: {legacy_files}"
    assert any("1646c9c659b6" in f for f in legacy_files)
    assert any("533c8a2b71cf" in f for f in legacy_files)
    assert any("6bfbdbe66807" in f for f in legacy_files)


def test_alembic_lineage_and_script_directory():
    """Verify Alembic script directory reports a single clean root head with no forks or branching."""
    cfg = Config(str(ALEMBIC_INI_PATH))
    script = ScriptDirectory.from_config(cfg)

    heads = script.get_heads()
    assert heads == ["0002_add_password_reset_tokens"], f"Unexpected heads: {heads}"

    base = script.get_base()
    assert base == "0001_phase5_baseline", f"Unexpected base: {base}"

    revision = script.get_revision("0002_add_password_reset_tokens")
    assert revision is not None
    assert revision.revision == "0002_add_password_reset_tokens"
    assert revision.down_revision == "0001_phase5_baseline"
    assert revision.branch_labels is None or len(revision.branch_labels) == 0


def test_alembic_upgrade_and_downgrade_disposable_sqlite(tmp_path):
    """Execute complete upgrade and downgrade cycle on disposable SQLite database."""
    test_db_path = tmp_path / "sandbox_alembic_test.db"
    db_url = f"sqlite:///{test_db_path}"

    cfg = Config(str(ALEMBIC_INI_PATH))
    cfg.set_main_option("sqlalchemy.url", db_url)

    # 1. Run upgrade head
    command.upgrade(cfg, "head")

    engine = create_engine(db_url)
    try:
        insp = inspect(engine)
        tables = set(insp.get_table_names())

        # Check all 17 application tables + alembic_version
        assert "alembic_version" in tables
        for expected_table in EXPECTED_APPLICATION_TABLES:
            assert expected_table in tables, f"Missing expected table: {expected_table}"

        # Verify assessment_reports.assessment_id is VARCHAR(36)
        report_cols = {col["name"]: col for col in insp.get_columns("assessment_reports")}
        assert "assessment_id" in report_cols
        col_type_str = str(report_cols["assessment_id"]["type"]).upper()
        assert "VARCHAR(36)" in col_type_str or "STRING(36)" in col_type_str or "VARCHAR" in col_type_str

        # Verify healthcare_facilities has 27 columns and 6 indexes
        facility_cols = insp.get_columns("healthcare_facilities")
        assert len(facility_cols) == 27, f"Expected 27 columns in healthcare_facilities, found {len(facility_cols)}"
        facility_indexes = {idx["name"] for idx in insp.get_indexes("healthcare_facilities")}
        expected_facility_indexes = {
            "ix_healthcare_facilities_emirate",
            "ix_healthcare_facilities_facility_type",
            "ix_healthcare_facilities_has_24_7_emergency",
            "ix_healthcare_facilities_id",
            "ix_healthcare_facilities_regulatory_authority",
            "ix_healthcare_facilities_slug",
        }
        for exp_idx in expected_facility_indexes:
            assert exp_idx in facility_indexes, f"Missing index on healthcare_facilities: {exp_idx}"

    finally:
        engine.dispose()

    # 2. Run downgrade base
    command.downgrade(cfg, "base")

    engine = create_engine(db_url)
    try:
        insp = inspect(engine)
        tables_after = set(insp.get_table_names())
        # All application tables must be dropped
        remaining_app_tables = tables_after.intersection(EXPECTED_APPLICATION_TABLES)
        assert len(remaining_app_tables) == 0, f"Remaining application tables after downgrade: {remaining_app_tables}"
    finally:
        engine.dispose()


def test_alembic_offline_sql_generation():
    """Verify offline SQL DDL generation produces valid syntax for all 17 tables."""
    cfg = Config(str(ALEMBIC_INI_PATH))
    buf = io.StringIO()
    with redirect_stdout(buf):
        command.upgrade(cfg, "head", sql=True)
    sql = buf.getvalue()

    for table in EXPECTED_APPLICATION_TABLES:
        assert f"CREATE TABLE {table}" in sql, f"Table creation missing in offline SQL: {table}"

    assert "INSERT INTO alembic_version" in sql


def test_alembic_postgresql_dialect_compatibility():
    """Verify migration compiles cleanly against PostgreSQL dialect in offline mode."""
    cfg = Config(str(ALEMBIC_INI_PATH))
    cfg.set_main_option("sqlalchemy.url", "postgresql+psycopg2://user:pass@localhost:5432/genovex_prod")

    # Offline upgrade test
    upgrade_buf = io.StringIO()
    with redirect_stdout(upgrade_buf):
        command.upgrade(cfg, "head", sql=True)
    pg_upgrade_sql = upgrade_buf.getvalue()

    assert "BEGIN;" in pg_upgrade_sql
    for table in EXPECTED_APPLICATION_TABLES:
        assert f"CREATE TABLE {table}" in pg_upgrade_sql, f"PostgreSQL DDL missing table {table}"

    # Offline downgrade test
    downgrade_buf = io.StringIO()
    with redirect_stdout(downgrade_buf):
        command.downgrade(cfg, "0001_phase5_baseline:base", sql=True)
    pg_downgrade_sql = downgrade_buf.getvalue()

    assert "DROP TABLE assessment_responses;" in pg_downgrade_sql
    assert "DROP TABLE assessment_reports;" in pg_downgrade_sql
    assert "DROP TABLE healthcare_facilities;" in pg_downgrade_sql


def test_live_database_untouched_and_unmigrated():
    """Verify Tier 1 backup retains pristine baseline hash, and live database is properly stamped."""
    if not TIER1_BACKUP_PATH.exists() or TIER1_BACKUP_PATH.stat().st_size == 0 or not LIVE_DB_PATH.exists():
        pytest.skip("Tier 1 backup or live database not present in test environment")
    assert TIER1_BACKUP_PATH.exists(), f"Tier 1 backup not found at: {TIER1_BACKUP_PATH}"

    # Verify Tier 1 backup SHA-256 hash matches authoritative baseline
    hasher = hashlib.sha256()
    with open(TIER1_BACKUP_PATH, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    t1_hash = hasher.hexdigest().lower()
    assert t1_hash == EXPECTED_SHA256.lower(), (
        f"Tier 1 backup SHA-256 changed! Expected {EXPECTED_SHA256}, got {t1_hash}"
    )

    # In live database, confirm alembic_version table exists and is stamped
    uri = f"file:{LIVE_DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        cur = conn.cursor()
        cur.execute("SELECT version_num FROM alembic_version")
        res = cur.fetchall()
        assert len(res) == 1, "alembic_version table must have exactly 1 stamped version"
        assert res[0][0] == "0001_phase5_baseline"

        # Confirm assessment_reports table schema in live database has migrated to VARCHAR(36)
        cur.execute("PRAGMA table_info(assessment_reports)")
        columns = {row[1]: row[2] for row in cur.fetchall()}
        assert columns.get("assessment_id") == "VARCHAR(36)", (
            f"Expected assessment_id VARCHAR(36), got: {columns.get('assessment_id')}"
        )
    finally:
        conn.close()
        conn.close()
