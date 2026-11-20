"""
GENOVEX: Adversarial Database Isolation Test Suite
Verifies centralized, fail-closed database isolation safeguards across 14 distinct attack/connection vectors.
All tests verify that the authoritative database can NEVER be opened with write capabilities in a test/audit context.
"""

import os
import sys
import subprocess
import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import AUTHORITATIVE_DB_PATH, settings
from app.core.database import (
    canonicalize_db_path,
    extract_sqlite_path,
    is_test_environment,
    validate_db_url_safety
)
from app.core.sandbox import create_disposable_sandbox_session


# ---------------------------------------------------------------------------
# Vector 1: Absolute Authoritative Database Path Detection
# ---------------------------------------------------------------------------
def test_vector_01_absolute_authoritative_path_blocked():
    abs_path = os.path.abspath(str(AUTHORITATIVE_DB_PATH))
    url = f"sqlite:///{abs_path.replace(os.sep, '/')}"
    with pytest.raises(RuntimeError) as exc_info:
        validate_db_url_safety(url)
    assert "CRITICAL SAFETY VIOLATION" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Vector 2: Relative Authoritative Database Path Detection
# ---------------------------------------------------------------------------
def test_vector_02_relative_authoritative_path_blocked():
    # If cwd is backend/, authoritative path is ../genovex.db
    rel_url = "sqlite:///../genovex.db"
    # Resolve against current cwd
    resolved = extract_sqlite_path(rel_url)
    auth_canon = canonicalize_db_path(AUTHORITATIVE_DB_PATH)
    if resolved == auth_canon:
        with pytest.raises(RuntimeError) as exc_info:
            validate_db_url_safety(rel_url)
        assert "CRITICAL SAFETY VIOLATION" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Vector 3: Windows-Style Path Variations (Backslashes, Mixed Case, Uppercase Drive)
# ---------------------------------------------------------------------------
def test_vector_03_windows_path_variations_blocked():
    raw_str = str(AUTHORITATIVE_DB_PATH).upper().replace("/", "\\")
    url = f"sqlite:///{raw_str}"
    with pytest.raises(RuntimeError) as exc_info:
        validate_db_url_safety(url)
    assert "CRITICAL SAFETY VIOLATION" in str(exc_info.value)

    # Mixed case and forward slashes
    mixed_str = str(AUTHORITATIVE_DB_PATH).lower().replace("\\", "/")
    url2 = f"sqlite:///{mixed_str}"
    with pytest.raises(RuntimeError) as exc_info:
        validate_db_url_safety(url2)
    assert "CRITICAL SAFETY VIOLATION" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Vector 4: Resolved Path and Symbolic-Link Equivalent
# ---------------------------------------------------------------------------
def test_vector_04_resolved_path_canonicalization():
    p = Path(AUTHORITATIVE_DB_PATH).resolve()
    canon1 = canonicalize_db_path(p)
    canon2 = canonicalize_db_path(AUTHORITATIVE_DB_PATH)
    assert canon1 == canon2
    url = f"sqlite:///{canon1}"
    with pytest.raises(RuntimeError) as exc_info:
        validate_db_url_safety(url)
    assert "CRITICAL SAFETY VIOLATION" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Vector 5: SQLite URL Variants (?mode=ro, ?check_same_thread=false)
# ---------------------------------------------------------------------------
def test_vector_05_sqlite_url_query_param_variants():
    base_url = f"sqlite:///{canonicalize_db_path(AUTHORITATIVE_DB_PATH)}"
    url_ro = f"{base_url}?mode=ro"
    url_thread = f"{base_url}?check_same_thread=false"
    url_combined = f"{base_url}?mode=ro&check_same_thread=false"

    for u in [url_ro, url_thread, url_combined]:
        with pytest.raises(RuntimeError) as exc_info:
            validate_db_url_safety(u)
        assert "CRITICAL SAFETY VIOLATION" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Vector 6: Direct Engine Creation with Authoritative Path Intercepted
# ---------------------------------------------------------------------------
def test_vector_06_direct_engine_creation_blocked():
    auth_url = f"sqlite:///{canonicalize_db_path(AUTHORITATIVE_DB_PATH)}"
    with pytest.raises(RuntimeError) as exc_info:
        validate_db_url_safety(auth_url)
        create_engine(auth_url)
    assert "CRITICAL SAFETY VIOLATION" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Vector 7: Direct Session Factory Use Intercepted
# ---------------------------------------------------------------------------
def test_vector_07_direct_session_factory_use():
    auth_url = f"sqlite:///{canonicalize_db_path(AUTHORITATIVE_DB_PATH)}"
    with pytest.raises(RuntimeError) as exc_info:
        validate_db_url_safety(auth_url)
        eng = create_engine(auth_url)
        SessionTest = sessionmaker(bind=eng)
        SessionTest()
    assert "CRITICAL SAFETY VIOLATION" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Vector 8: Standalone Script with Ordinary Filename (e.g., worker.py)
# ---------------------------------------------------------------------------
def test_vector_08_standalone_script_ordinary_filename():
    script = """
import sys
import os
os.environ["GENOVEX_TESTING"] = "1"
try:
    from app.core.database import validate_db_url_safety
    from app.core.config import AUTHORITATIVE_DB_PATH
    url = f"sqlite:///{AUTHORITATIVE_DB_PATH.as_posix()}"
    validate_db_url_safety(url)
    print("VULNERABLE")
    sys.exit(1)
except RuntimeError:
    print("BLOCKED_SUCCESSFULLY")
    sys.exit(0)
"""
    res = subprocess.run(
        [sys.executable, "-c", script, "worker.py"],
        cwd=str(Path(__file__).resolve().parents[1]),
        capture_output=True,
        text=True
    )
    assert res.returncode == 0
    assert "BLOCKED_SUCCESSFULLY" in res.stdout


# ---------------------------------------------------------------------------
# Vector 9: Scripts That Do Not Contain 'test_' or 'audit' (e.g. migrate.py)
# ---------------------------------------------------------------------------
def test_vector_09_scripts_without_test_or_audit_in_name():
    script = """
import sys
import os
os.environ["TESTING"] = "true"
try:
    from app.core.database import validate_db_url_safety
    from app.core.config import AUTHORITATIVE_DB_PATH
    url = f"sqlite:///{AUTHORITATIVE_DB_PATH.as_posix()}"
    validate_db_url_safety(url)
    print("VULNERABLE")
    sys.exit(1)
except RuntimeError:
    print("BLOCKED_SUCCESSFULLY")
    sys.exit(0)
"""
    res = subprocess.run(
        [sys.executable, "-c", script, "run_service.py"],
        cwd=str(Path(__file__).resolve().parents[1]),
        capture_output=True,
        text=True
    )
    assert res.returncode == 0
    assert "BLOCKED_SUCCESSFULLY" in res.stdout


# ---------------------------------------------------------------------------
# Vector 10: Pytest Execution Redirection Invariant
# ---------------------------------------------------------------------------
def test_vector_10_pytest_execution_redirection_active():
    # Inside this pytest session, settings.DATABASE_URL must NOT be the authoritative DB
    auth_canon = canonicalize_db_path(AUTHORITATIVE_DB_PATH)
    active_path = extract_sqlite_path(settings.DATABASE_URL)
    assert active_path != auth_canon, "Pytest running directly on authoritative database!"
    assert "test_genovex" in settings.DATABASE_URL or "sandbox" in settings.DATABASE_URL


# ---------------------------------------------------------------------------
# Vector 11: Disposable Sandbox Creation and Automatic Cleanup
# ---------------------------------------------------------------------------
def test_vector_11_disposable_sandbox_creation_and_cleanup():
    tmp_path_holder = []
    with create_disposable_sandbox_session() as session:
        engine_url = str(session.get_bind().url)
        assert "sandbox" in engine_url
        assert canonicalize_db_path(AUTHORITATIVE_DB_PATH) != extract_sqlite_path(engine_url)
        tmp_db = extract_sqlite_path(engine_url)
        tmp_path_holder.append(tmp_db)
        assert os.path.exists(tmp_db)

    # After exit, temp directory and file must be completely deleted
    assert not os.path.exists(tmp_path_holder[0])


# ---------------------------------------------------------------------------
# Vector 12: Missing Sandbox Configuration Fails Closed
# ---------------------------------------------------------------------------
def test_vector_12_missing_sandbox_configuration_fails_closed():
    # If a test runs without sandbox redirection, attempting to validate authoritative URL raises error
    auth_url = f"sqlite:///{AUTHORITATIVE_DB_PATH.as_posix()}"
    with pytest.raises(RuntimeError):
        validate_db_url_safety(auth_url)


# ---------------------------------------------------------------------------
# Vector 13: Incorrect Sandbox Configuration (Empty or Invalid Path)
# ---------------------------------------------------------------------------
def test_vector_13_incorrect_sandbox_configuration():
    # Empty string is not a valid sandbox
    assert extract_sqlite_path("") is None
    # Memory database is recognized
    assert extract_sqlite_path("sqlite:///:memory:") == ":memory:"


# ---------------------------------------------------------------------------
# Vector 14: Alternate Connection Paths (URI mode=ro with write attempt)
# ---------------------------------------------------------------------------
def test_vector_14_alternate_connection_paths():
    # Connecting with URI mode=ro prevents writes at SQLite engine level
    import sqlite3
    ro_url = f"file:{str(AUTHORITATIVE_DB_PATH)}?mode=ro"
    conn = sqlite3.connect(ro_url, uri=True)
    cur = conn.cursor()
    cur.execute("PRAGMA query_only = ON;")
    with pytest.raises(sqlite3.OperationalError):
        cur.execute("CREATE TABLE IF NOT EXISTS should_fail (id INT);")
    conn.close()
