import os
import sys
import contextlib
import shutil
import tempfile
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings, AUTHORITATIVE_DB_PATH

def is_test_environment() -> bool:
    """Detect whether code is running inside a test runner, test script, or audit script."""
    if os.getenv("PYTEST_CURRENT_TEST"):
        return True
    if "pytest" in sys.modules or any("pytest" in arg.lower() for arg in sys.argv):
        return True
    if os.getenv("GENOVEX_TESTING", "").lower() in ("1", "true"):
        return True
    if sys.argv and any(arg.endswith(".py") and ("test_" in os.path.basename(arg) or "audit" in os.path.basename(arg)) for arg in sys.argv):
        return True
    return False

# Permanent database isolation safeguard
auth_canonical = os.path.abspath(str(AUTHORITATIVE_DB_PATH)).lower().replace(os.sep, "/")
configured_url = settings.DATABASE_URL.lower().replace(os.sep, "/")

if is_test_environment() and auth_canonical in configured_url:
    raise RuntimeError(
        f"CRITICAL SAFETY VIOLATION: Execution in test/audit environment attempted to bind to "
        f"authoritative database '{AUTHORITATIVE_DB_PATH}'! "
        f"You must use a disposable sandbox database URL (e.g. via conftest.py or create_disposable_sandbox_session)."
    )

# For SQLite, check_same_thread needs to be False for concurrent FastAPI workers
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

# Apply SQLite reliability pragmas on connection
if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA foreign_keys=ON")
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
    """
    src = str(source_db_path or AUTHORITATIVE_DB_PATH)
    tmp_dir = tempfile.mkdtemp(prefix="genovex_disposable_sandbox_")
    tmp_db_path = os.path.join(tmp_dir, "sandbox.db")
    if os.path.exists(src):
        shutil.copyfile(src, tmp_db_path)
    tmp_url = f"sqlite:///{tmp_db_path.replace(os.sep, '/')}"
    tmp_engine = create_engine(tmp_url, connect_args={"check_same_thread": False}, echo=False)
    TmpSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=tmp_engine)
    session = TmpSessionLocal()
    try:
        yield session
    finally:
        session.close()
        tmp_engine.dispose()
        shutil.rmtree(tmp_dir, ignore_errors=True)

# Explicitly import all declarative models to register with Base.metadata
def register_models():
    import app.models.medical_content  # noqa: F401
    import app.models.questionnaire    # noqa: F401
    import app.models.clinical_rules   # noqa: F401
    import app.models.assessment_report # noqa: F401
    import app.models.facility         # noqa: F401
    try:
        from app.core.security import User, AuditLog # noqa: F401
    except (ImportError, AttributeError):
        pass

register_models()
