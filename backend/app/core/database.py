import os
import sys
import contextlib
import shutil
import tempfile
from pathlib import Path
from typing import Optional
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings, AUTHORITATIVE_DB_PATH

def canonicalize_db_path(path_str: str | Path) -> str:
    """Canonicalize a filesystem path resolving symlinks, case folding, and Windows separators."""
    try:
        p = Path(path_str).resolve()
        return str(p).lower().replace("\\", "/")
    except Exception:
        return str(path_str).lower().replace("\\", "/")

def extract_sqlite_path(db_url: str) -> Optional[str]:
    """Parses a SQLite connection URL and extracts the canonical physical filesystem path."""
    if not db_url or not db_url.startswith("sqlite"):
        return None
    # Strip scheme prefix
    url_body = db_url[len("sqlite:"):].lstrip("/")
    from urllib.parse import unquote
    url_body = unquote(url_body)
    # Handle pure in-memory SQLite databases
    if url_body.startswith(":memory:"):
        return ":memory:"
    # Strip query string arguments (?mode=ro, ?check_same_thread=false)
    path_clean = url_body.split("?")[0]
    return canonicalize_db_path(path_clean)

def is_test_environment() -> bool:
    """Detect whether code is running inside a test runner, test script, or audit script."""
    if os.getenv("PYTEST_CURRENT_TEST"):
        return True
    if "pytest" in sys.modules or any("pytest" in arg.lower() for arg in sys.argv):
        return True
    if os.getenv("GENOVEX_TESTING", "").lower() in ("1", "true"):
        return True
    if os.getenv("TESTING", "").lower() in ("1", "true"):
        return True
    if sys.argv and any(arg.endswith(".py") and any(k in os.path.basename(arg).lower() for k in ["test_", "audit", "check_", "verify_"]) for arg in sys.argv):
        return True
    return False

def validate_db_url_safety(db_url: str) -> None:
    """
    FAIL-CLOSED SAFETY POLICY:
    Verifies that a database URL does not bind to the authoritative database during test/audit execution.
    Raises RuntimeError before any engine or connection is established.
    """
    if not is_test_environment():
        return
    parsed_path = extract_sqlite_path(db_url)
    auth_path = canonicalize_db_path(AUTHORITATIVE_DB_PATH)
    if parsed_path == auth_path:
        raise RuntimeError(
            f"CRITICAL SAFETY VIOLATION: Execution in test/audit environment attempted to bind to "
            f"authoritative database '{AUTHORITATIVE_DB_PATH}'!\n"
            f"Configured URL: {db_url}\n"
            f"Canonical Target: {parsed_path}\n"
            f"Authoritative Canonical: {auth_path}\n"
            f"You must use an isolated disposable sandbox database URL (e.g. via conftest.py or create_disposable_sandbox_session)."
        )

# Enforce fail-closed check on configured DATABASE_URL
validate_db_url_safety(settings.DATABASE_URL)

# For SQLite, check_same_thread needs to be False for concurrent FastAPI workers
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

# Mandatory connection listener for SQLite: Enables WAL reliability pragmas, foreign keys & connection-level write blocking
if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            
            # Secondary connection-level guard: if test environment somehow checked out connection to auth DB
            if is_test_environment():
                parsed_path = extract_sqlite_path(settings.DATABASE_URL)
                auth_path = canonicalize_db_path(AUTHORITATIVE_DB_PATH)
                if parsed_path == auth_path:
                    cursor.execute("PRAGMA query_only=ON;")
                    raise RuntimeError("CRITICAL SAFETY VIOLATION: Blocked attempted connection checkout to authoritative database!")
        finally:
            cursor.close()

    # Refresh engine pool so that subsequent checkouts inherit the connection listener
    engine.dispose()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextlib.contextmanager
def create_disposable_sandbox_session(source_db_path=None):
    """
    Creates an isolated temporary sandbox database from source_db_path (defaults to AUTHORITATIVE_DB_PATH)
    and yields a SQLAlchemy Session. Automatically disposes and deletes the temporary database upon exit.
    This guarantees zero writes to the authoritative database file.
    """
    from app.core.sandbox import create_disposable_sandbox_session as _sandbox_mgr
    with _sandbox_mgr(source_db_path) as session:
        yield session

# Explicitly import all declarative models to register with Base.metadata
def register_models():
    try:
        import app.models.medical_content  # noqa: F401
    except (ImportError, AttributeError):
        pass
    try:
        import app.models.questionnaire    # noqa: F401
    except (ImportError, AttributeError):
        pass
    try:
        import app.models.clinical_rules   # noqa: F401
    except (ImportError, AttributeError):
        pass
    try:
        import app.models.assessment_report # noqa: F401
    except (ImportError, AttributeError):
        pass
    try:
        import app.models.facility         # noqa: F401
    except (ImportError, AttributeError):
        pass
    try:
        from app.core.security import User, AuditLog # noqa: F401
    except (ImportError, AttributeError):
        pass

register_models()
