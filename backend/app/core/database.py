from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

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
