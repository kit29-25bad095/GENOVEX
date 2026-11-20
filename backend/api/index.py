"""
Vercel Serverless Function entrypoint for GENOVEX FastAPI backend (backend-relative).
Exports ASGI application instance 'app' for Vercel Python runtime.
"""

import sys
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = BACKEND_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DATABASE_URL", f"sqlite:///{BASE_DIR / 'genovex.db'}")

from main import app
