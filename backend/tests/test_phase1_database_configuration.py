"""
GENOVEX: Phase 1 Database Configuration & Path Resolution Verification Suite
Validates resolution of 'Development SQLite path fallback in default settings':
1. Default development SQLite path resolution to canonical AUTHORITATIVE_DB_PATH.
2. Explicit database URL/path overriding default.
3. Deterministic path resolution anchored to PROJECT_ROOT regardless of process working directory.
4. Clean directory verification and creation for file-based SQLite databases.
5. Strict test database isolation and fail-closed protections.
6. Production and staging environments strictly refuse unsafe SQLite fallbacks or missing URLs.
7. Clear, descriptive error messages for invalid or unsupported configuration schemes.
8. Authoritative database file integrity and schema compatibility preservation.
"""

import os
import sys
import sqlite3
import tempfile
import pytest
from pathlib import Path

from app.core.config import (
    Settings,
    PROJECT_ROOT,
    AUTHORITATIVE_DB_PATH,
    normalize_database_url,
    is_sqlite_path_absolute
)
from app.core.database import (
    canonicalize_db_path,
    extract_sqlite_path,
    validate_db_url_safety,
    create_configured_engine
)


# ---------------------------------------------------------------------------
# Requirement 1: Default Development SQLite Path Resolution
# ---------------------------------------------------------------------------
def test_default_dev_sqlite_path_resolution():
    """Verify that in development without explicit DATABASE_URL, Settings defaults canonically to genovex.db."""
    dev_settings = Settings(
        ENVIRONMENT="development",
        DATABASE_URL="",
        SECRET_KEY="c4ca4238a0b923820dcc509a6f75849b"
    )
    expected_url = f"sqlite:///{AUTHORITATIVE_DB_PATH.as_posix()}"
    assert dev_settings.DATABASE_URL == expected_url
    assert "genovex.db" in dev_settings.DATABASE_URL


# ---------------------------------------------------------------------------
# Requirement 2: Explicit Database URL Overrides Default
# ---------------------------------------------------------------------------
def test_explicit_database_url_overrides_default():
    """Verify that an explicit DATABASE_URL overrides any default fallback."""
    # 1. PostgreSQL URL
    pg_url = "postgresql://genovex_app:db_pass@db.internal:5432/genovex_prod"
    pg_settings = Settings(
        ENVIRONMENT="development",
        DATABASE_URL=pg_url,
        SECRET_KEY="c4ca4238a0b923820dcc509a6f75849b"
    )
    assert pg_settings.DATABASE_URL == pg_url

    # 2. Legacy postgres:// normalized to postgresql://
    legacy_pg = "postgres://genovex_app:db_pass@db.internal:5432/genovex_prod"
    legacy_settings = Settings(
        ENVIRONMENT="development",
        DATABASE_URL=legacy_pg,
        SECRET_KEY="c4ca4238a0b923820dcc509a6f75849b"
    )
    assert legacy_settings.DATABASE_URL.startswith("postgresql://")

    # 3. In-memory SQLite
    mem_settings = Settings(
        ENVIRONMENT="development",
        DATABASE_URL="sqlite:///:memory:",
        SECRET_KEY="c4ca4238a0b923820dcc509a6f75849b"
    )
    assert mem_settings.DATABASE_URL == "sqlite:///:memory:"


# ---------------------------------------------------------------------------
# Requirement 3: Working Directory Invariance (No Split-Brain Databases)
# ---------------------------------------------------------------------------
def test_relative_path_resolution_anchored_to_project_root():
    """Verify that relative SQLite paths resolve relative to PROJECT_ROOT regardless of process CWD."""
    orig_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as foreign_dir:
        try:
            os.chdir(foreign_dir)
            # Resolve relative URL './genovex.db'
            norm_url = normalize_database_url(
                raw_url="sqlite:///./genovex.db",
                environment="development",
                base_dir=PROJECT_ROOT
            )
            expected_canon = AUTHORITATIVE_DB_PATH.resolve().as_posix().lower()
            assert expected_canon in norm_url.lower()

            # Verify canonicalize_db_path is also anchored to PROJECT_ROOT
            canon_path = canonicalize_db_path("./genovex.db")
            assert canon_path == canonicalize_db_path(AUTHORITATIVE_DB_PATH)

            # Verify no split-brain database file was created in the foreign CWD
            assert not (Path(foreign_dir) / "genovex.db").exists()
        finally:
            os.chdir(orig_cwd)


# ---------------------------------------------------------------------------
# Requirement 4: Missing Database Directory Clean Handling & Auto-Creation
# ---------------------------------------------------------------------------
def test_missing_database_directory_auto_created():
    """Verify that non-existent parent directories for file SQLite paths are safely created."""
    with tempfile.TemporaryDirectory() as tmp_base:
        target_db = Path(tmp_base) / "nested_dir" / "deeper_dir" / "sandbox.db"
        assert not target_db.parent.exists()

        custom_url = f"sqlite:///{target_db.as_posix()}"
        norm_url = normalize_database_url(
            raw_url=custom_url,
            environment="development",
            base_dir=PROJECT_ROOT
        )
        # Parent directory must now exist
        assert target_db.parent.exists()
        assert target_db.parent.is_dir()

        # Engine creation should succeed without OperationalError
        eng = create_configured_engine(norm_url)
        try:
            with eng.connect() as conn:
                from sqlalchemy import text
                res = conn.execute(text("SELECT 1;")).scalar()
                assert res == 1
        finally:
            eng.dispose()


# ---------------------------------------------------------------------------
# Requirement 5: Test Database Isolation & Fail-Closed Protection
# ---------------------------------------------------------------------------
def test_test_database_isolation_enforced():
    """Verify that test environments reject connection attempts to the authoritative database."""
    auth_url = f"sqlite:///{AUTHORITATIVE_DB_PATH.as_posix()}"
    with pytest.raises(RuntimeError, match="CRITICAL SAFETY VIOLATION"):
        validate_db_url_safety(auth_url)

    # Relative path pointing to authoritative DB must also be intercepted
    with pytest.raises(RuntimeError, match="CRITICAL SAFETY VIOLATION"):
        validate_db_url_safety("sqlite:///./genovex.db")


# ---------------------------------------------------------------------------
# Requirement 6: Production Configuration Refuses Unsafe SQLite Fallback
# ---------------------------------------------------------------------------
def test_production_refuses_unsafe_sqlite_fallback():
    """Verify that production and staging fail closed if DATABASE_URL is missing or unsafe."""
    # 1. Missing DATABASE_URL in production raises ValueError
    with pytest.raises(ValueError, match="DATABASE_URL must be explicitly configured in production"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            SECRET_KEY="c4ca4238a0b923820dcc509a6f75849b",
            DATABASE_URL=""
        )

    # 2. Missing DATABASE_URL in staging raises ValueError
    with pytest.raises(ValueError, match="DATABASE_URL must be explicitly configured in staging"):
        Settings(
            ENVIRONMENT="staging",
            DEBUG=False,
            SECRET_KEY="c4ca4238a0b923820dcc509a6f75849b",
            DATABASE_URL=""
        )

    # 3. VERCEL_ENV=production enforces checks even if ENVIRONMENT=development
    os.environ["VERCEL_ENV"] = "production"
    try:
        with pytest.raises(ValueError, match="DATABASE_URL must be explicitly configured in development"):
            Settings(
                ENVIRONMENT="development",
                DEBUG=False,
                SECRET_KEY="c4ca4238a0b923820dcc509a6f75849b",
                DATABASE_URL=""
            )
    finally:
        os.environ.pop("VERCEL_ENV", None)

    # 4. Attempting to use dev SQLite genovex.db in production raises ValueError
    with pytest.raises(ValueError, match="Binding to development database 'genovex.db' is strictly prohibited"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            SECRET_KEY="c4ca4238a0b923820dcc509a6f75849b",
            DATABASE_URL=f"sqlite:///{AUTHORITATIVE_DB_PATH.as_posix()}"
        )

    # 5. Relative SQLite path in production raises ValueError
    with pytest.raises(ValueError, match="Relative SQLite database path.*is prohibited"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            SECRET_KEY="c4ca4238a0b923820dcc509a6f75849b",
            DATABASE_URL="sqlite:///./prod.db"
        )

    # 6. Valid PostgreSQL configuration in production succeeds
    valid_prod = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        SECRET_KEY="c4ca4238a0b923820dcc509a6f75849b",
        DATABASE_URL="postgresql://prod_user:vault_pass@postgres.cluster:5432/genovex_prod"
    )
    assert valid_prod.DATABASE_URL == "postgresql://prod_user:vault_pass@postgres.cluster:5432/genovex_prod"


# ---------------------------------------------------------------------------
# Requirement 7: Invalid Configuration Produces Understandable Errors
# ---------------------------------------------------------------------------
def test_invalid_configuration_produces_clear_error():
    """Verify that unsupported URL schemes or malformed configurations raise clear errors."""
    with pytest.raises(ValueError, match="Unsupported database URL scheme 'mysql'"):
        normalize_database_url(
            raw_url="mysql://user:pass@localhost:3306/db",
            environment="development"
        )

    with pytest.raises(ValueError, match="Unsupported database URL scheme 'mongodb'"):
        normalize_database_url(
            raw_url="mongodb://localhost:27017/db",
            environment="development"
        )


# ---------------------------------------------------------------------------
# Requirement 8: Authoritative Database Integrity Preservation
# ---------------------------------------------------------------------------
def test_authoritative_database_remains_intact():
    """Verify that authoritative genovex.db is intact, uncorrupted, and has 18 tables."""
    assert AUTHORITATIVE_DB_PATH.exists(), "Authoritative genovex.db file missing!"
    file_size = AUTHORITATIVE_DB_PATH.stat().st_size
    assert file_size >= 4_000_000, f"Database size suspicious ({file_size} bytes)"

    # Read-only verification
    ro_uri = f"file:{AUTHORITATIVE_DB_PATH.resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(ro_uri, uri=True)
    try:
        cur = conn.cursor()
        integrity = cur.execute("PRAGMA integrity_check;").fetchall()
        assert integrity == [("ok",)], f"Database failed integrity check: {integrity}"

        tables = [
            row[0] for row in cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
            ).fetchall()
        ]
        assert len(tables) == 19, f"Expected 19 tables, found {len(tables)}: {tables}"
        assert "users" in tables
        assert "clinical_rules" in tables
        assert "questionnaire_versions" in tables
        assert "questions" in tables
        assert "assessment_reports" in tables
        assert "healthcare_facilities" in tables
        assert "password_reset_tokens" in tables
    finally:
        conn.close()
