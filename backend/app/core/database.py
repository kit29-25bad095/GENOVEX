import os
import sys
import contextlib
import shutil
import tempfile
from pathlib import Path
from typing import Optional
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings, AUTHORITATIVE_DB_PATH, PROJECT_ROOT

def canonicalize_db_path(path_str: str | Path) -> str:
    """Canonicalize a filesystem path resolving symlinks, case folding, and Windows separators.
    Relative paths are resolved deterministically relative to PROJECT_ROOT regardless of process working directory.
    """
    try:
        norm = str(path_str).replace("\\", "/")
        p = Path(norm)
        if not (p.is_absolute() or norm.startswith('/') or bool(p.drive)):
            p = PROJECT_ROOT / p
        return str(p.resolve()).lower().replace("\\", "/")
    except Exception:
        return str(path_str).lower().replace("\\", "/")

def extract_sqlite_path(db_url: str) -> Optional[str]:
    """Parses a SQLite connection URL and extracts the canonical physical filesystem path."""
    if not db_url or not db_url.startswith("sqlite"):
        return None
    url_body = db_url.split("?")[0]
    if url_body.startswith("sqlite:"):
        url_body = url_body[len("sqlite:"):]
    norm_body = url_body.replace("\\", "/")
    clean = norm_body.lstrip("/")
    from urllib.parse import unquote
    clean = unquote(clean)
    if clean.startswith(":memory:"):
        return ":memory:"
    if norm_body.startswith("///"):
        path_part = norm_body[3:]
    elif norm_body.startswith("//"):
        path_part = norm_body[2:]
    else:
        path_part = norm_body
    path_part = unquote(path_part)
    return canonicalize_db_path(path_part)

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

def set_sqlite_pragma(dbapi_connection, connection_record):
    """Configures high-performance WAL mode and foreign key constraint enforcement for SQLite."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()

def create_configured_engine(db_url: str):
    """
    Factory function to configure a production-ready SQLAlchemy Engine.
    Handles PostgreSQL (with connection pooling) vs SQLite (with thread safety & WAL pragmas).
    """
    if db_url.startswith("postgres://") or db_url.startswith("postgresql"):
        # Normalize legacy postgres:// to postgresql:// for SQLAlchemy 2.0+
        normalized_url = db_url.replace("postgres://", "postgresql://", 1) if db_url.startswith("postgres://") else db_url
        return create_engine(
            normalized_url,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            pool_recycle=settings.DB_POOL_RECYCLE,
            pool_pre_ping=settings.DB_POOL_PRE_PING,
            echo=False
        )
    elif db_url.startswith("sqlite"):
        sqlite_path = extract_sqlite_path(db_url)
        if sqlite_path and sqlite_path != ":memory:":
            try:
                Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
        connect_args = {"check_same_thread": False}
        sqlite_engine = create_engine(
            db_url,
            connect_args=connect_args,
            pool_pre_ping=settings.DB_POOL_PRE_PING,
            echo=False
        )
        event.listen(sqlite_engine, "connect", set_sqlite_pragma)
        sqlite_engine.dispose()
        return sqlite_engine
    else:
        return create_engine(db_url, pool_pre_ping=settings.DB_POOL_PRE_PING, echo=False)

engine = create_configured_engine(settings.DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
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
    try:
        import app.models.password_reset   # noqa: F401
    except (ImportError, AttributeError):
        pass

register_models()
