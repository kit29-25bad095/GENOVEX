import sys
import os
import shutil
import tempfile
import atexit
import importlib.metadata
from unittest.mock import MagicMock

# 1. Shim email-validator for test execution when optional dependency is not yet installed in test runner environment
if "email_validator" not in sys.modules:
    try:
        import email_validator  # noqa: F401
    except ImportError:
        mock_ev = MagicMock()
        mock_ev.EmailNotValidError = ValueError
        def _mock_validate_email(email, check_deliverability=False):
            return type("ValidatedEmail", (), {"normalized": email})()
        mock_ev.validate_email = _mock_validate_email
        sys.modules["email_validator"] = mock_ev

        _orig_version = importlib.metadata.version
        def _mock_version(distribution_name: str) -> str:
            if distribution_name == "email-validator":
                return "2.2.0"
            return _orig_version(distribution_name)
        importlib.metadata.version = _mock_version

# 2. Database sandbox isolation: Copy live database to temporary sandbox for all tests
# This ensures that running pytest NEVER modifies the live genovex.db file.
import pytest
from app.core import config
from app.core.config import AUTHORITATIVE_DB_PATH

if os.path.exists(AUTHORITATIVE_DB_PATH):
    _test_tmp_dir = tempfile.mkdtemp(prefix="genovex_test_sandbox_")
    _test_db_path = os.path.join(_test_tmp_dir, "test_genovex.db")
    shutil.copyfile(AUTHORITATIVE_DB_PATH, _test_db_path)
    # Re-target config settings and database engine to the disposable sandbox copy
    sandbox_url = f"sqlite:///{_test_db_path.replace(os.sep, '/')}"
    config.settings.DATABASE_URL = sandbox_url

    # Rebind engine and SessionLocal in app.core.database
    import app.core.database
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    connect_args = {"check_same_thread": False} if sandbox_url.startswith("sqlite") else {}
    app.core.database.engine = create_engine(sandbox_url, connect_args=connect_args, echo=False)
    app.core.database.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=app.core.database.engine)

    def _cleanup():
        try:
            app.core.database.engine.dispose()
        except Exception:
            pass
        try:
            shutil.rmtree(_test_tmp_dir, ignore_errors=True)
        except Exception:
            pass

    atexit.register(_cleanup)

@pytest.fixture(autouse=True, scope="function")
def verify_disposable_database_isolation():
    """
    CRITICAL SAFETY INVARIANT:
    Aborts any test execution if DATABASE_URL or active engine resolves to the authoritative database path.
    """
    auth_canonical = os.path.abspath(str(AUTHORITATIVE_DB_PATH)).lower().replace(os.sep, "/")
    configured_url = config.settings.DATABASE_URL.lower().replace(os.sep, "/")
    if auth_canonical in configured_url:
        raise RuntimeError(
            f"CRITICAL SAFETY VIOLATION: Test runner configured with authoritative database path!\n"
            f"Configured URL: {config.settings.DATABASE_URL}\n"
            f"Authoritative Path: {AUTHORITATIVE_DB_PATH}"
        )

    import app.core.database
    engine_url = str(app.core.database.engine.url).lower().replace(os.sep, "/")
    if auth_canonical in engine_url:
        raise RuntimeError(
            f"CRITICAL SAFETY VIOLATION: SQLAlchemy engine resolves to authoritative database!\n"
            f"Engine URL: {app.core.database.engine.url}\n"
            f"Authoritative Path: {AUTHORITATIVE_DB_PATH}"
        )

