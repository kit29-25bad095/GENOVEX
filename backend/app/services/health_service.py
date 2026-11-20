import time
import os
import shutil
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal

class HealthService:
    """
    Comprehensive multi-tier health monitoring service.
    Evaluates database responsiveness, disk space, and application runtime.
    Categorizes system state as: 'healthy', 'degraded', or 'unavailable'.
    """

    @classmethod
    def check_database(cls, db: Optional[Session] = None) -> Dict[str, Any]:
        """Pings the database and measures response latency."""
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True

        start_time = time.perf_counter()
        try:
            db.execute(text("SELECT 1")).scalar()
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "status": "healthy",
                "latency_ms": latency_ms,
                "engine": "sqlite" if settings.DATABASE_URL.startswith("sqlite") else "postgresql"
            }
        except Exception as e:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "status": "unavailable",
                "latency_ms": latency_ms,
                "error": "Database connectivity failed"
            }
        finally:
            if should_close:
                db.close()

    @classmethod
    def check_storage(cls) -> Dict[str, Any]:
        """Checks disk availability for database and backup operations."""
        try:
            db_path = settings.DATABASE_URL.replace("sqlite:///", "").replace("./", "")
            base_dir = os.path.dirname(os.path.abspath(db_path)) if os.path.isabs(db_path) else os.getcwd()
            total, used, free = shutil.disk_usage(base_dir)
            free_mb = round(free / (1024 * 1024), 2)
            is_low_space = free_mb < 500  # Alert if < 500 MB free
            return {
                "status": "degraded" if is_low_space else "healthy",
                "free_disk_mb": free_mb,
                "low_disk_warning": is_low_space
            }
        except Exception:
            return {
                "status": "degraded",
                "error": "Disk storage metric unavailable"
            }

    @classmethod
    def get_public_health(cls, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Public health endpoint response.
        Safe for load balancers and uptime checkers.
        Never exposes sensitive paths, credentials, or internal stack traces.
        """
        db_health = cls.check_database(db)
        overall_status = "healthy"
        if db_health["status"] == "unavailable":
            overall_status = "unavailable"
        elif db_health["status"] == "degraded":
            overall_status = "degraded"

        return {
            "status": overall_status,
            "platform": settings.PROJECT_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "market": "UAE",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": {
                "database": db_health["status"],
                "api": "healthy"
            }
        }

    @classmethod
    def get_detailed_diagnostics(cls, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Detailed diagnostics reserved for authorized administrators and clinical reviewers.
        Includes latencies, disk space, and uptime telemetry.
        """
        db_health = cls.check_database(db)
        storage_health = cls.check_storage()

        # Compute overall state
        overall = "healthy"
        if db_health["status"] == "unavailable":
            overall = "unavailable"
        elif db_health["status"] == "degraded" or storage_health["status"] == "degraded":
            overall = "degraded"

        return {
            "status": overall,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "platform": settings.PROJECT_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "checks": {
                "database": db_health,
                "storage": storage_health,
                "logging": {
                    "structured_logging_enabled": settings.ENABLE_STRUCTURED_LOGGING,
                    "log_level": settings.LOG_LEVEL
                },
                "scheduler": {
                    "enabled": settings.ENABLE_BACKGROUND_SCHEDULER,
                    "interval_minutes": settings.MAINTENANCE_INTERVAL_MINUTES
                }
            }
        }
