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
