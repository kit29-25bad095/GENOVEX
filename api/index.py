"""
Vercel Serverless Function entrypoint for GENOVEX FastAPI backend.
Exports ASGI application instance 'app' for Vercel Python runtime.
"""

import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
    import shutil
    tmp_db = Path("/tmp/genovex.db")
    src_db = BASE_DIR / "genovex.db"
    if src_db.exists() and not tmp_db.exists():
        try:
            shutil.copy2(src_db, tmp_db)
        except Exception:
            pass
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_db}"
else:
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{BASE_DIR / 'genovex.db'}")

from main import app

# Ensure tables and baseline seed data exist in serverless environments (e.g. Vercel)
if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
    try:
        from app.core.database import engine, Base, SessionLocal
        from sqlalchemy import inspect
        inspector = inspect(engine)
        if "questionnaire_versions" not in inspector.get_table_names():
            Base.metadata.create_all(bind=engine)
            db = SessionLocal()
            try:
                from app.core.seed_data import seed_database
                from app.core.seed_questionnaire import seed_questionnaire_v1
                from app.core.seed_clinical_rules import seed_clinical_rules_v1
                from app.core.seed_facilities import seed_facilities_v1
                seed_database(db)
                seed_questionnaire_v1(db)
                seed_clinical_rules_v1(db)
                seed_facilities_v1(db)
            finally:
                db.close()
    except Exception as e:
        print(f"Warning: Serverless DB auto-init exception: {e}")
