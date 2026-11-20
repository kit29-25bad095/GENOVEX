import os
import shutil
import tempfile
import contextlib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings, AUTHORITATIVE_DB_PATH

@contextlib.contextmanager
def create_disposable_sandbox_session(source_db_path=None):
    """
    Creates an isolated temporary sandbox database from source_db_path (defaults to AUTHORITATIVE_DB_PATH)
    and yields a SQLAlchemy Session. Automatically disposes and deletes the temporary database upon exit.
    This guarantees zero writes to the authoritative database file.
    """
    src = str(source_db_path or AUTHORITATIVE_DB_PATH)
    tmp_dir = tempfile.mkdtemp(prefix="genovex_disposable_sandbox_")
    tmp_db_path = os.path.join(tmp_dir, "sandbox.db")
    if os.path.exists(src):
        shutil.copyfile(src, tmp_db_path)
    tmp_url = f"sqlite:///{tmp_db_path.replace(os.sep, '/')}"
    
    # Temporarily redirect global settings.DATABASE_URL so any imported modules bind to sandbox
    orig_url = settings.DATABASE_URL
    settings.DATABASE_URL = tmp_url
    
    tmp_engine = create_engine(tmp_url, connect_args={"check_same_thread": False}, echo=False)
    TmpSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=tmp_engine)
    session = TmpSessionLocal()
    try:
        yield session
    finally:
        session.close()
        tmp_engine.dispose()
        settings.DATABASE_URL = orig_url
        shutil.rmtree(tmp_dir, ignore_errors=True)
