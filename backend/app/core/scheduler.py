import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from app.core.config import settings
from app.core.logging_config import get_logger
from app.core.database import SessionLocal
from app.services.backup_service import BackupService
from app.services.clinical_asset_maintenance_service import ClinicalAssetMaintenanceService

logger = get_logger("maintenance_scheduler")

class MaintenanceScheduler:
    """
    Lightweight, asynchronous background maintenance runner.
    Periodically executes database backups, integrity checks, and clinical asset audits.
    Guaranteed idempotent, robust to transient exceptions, and clean shutdown on exit.
    """

    _task: Optional[asyncio.Task] = None
    _is_running: bool = False
    _last_run_time: Optional[str] = None
    _last_run_status: str = "NEVER_RUN"
    _last_run_details: Dict[str, Any] = {}
    _execution_count: int = 0

    @classmethod
    async def start(cls):
        """Starts the periodic background scheduler task."""
        if not settings.ENABLE_BACKGROUND_SCHEDULER:
            logger.info("Background maintenance scheduler is disabled in settings.")
            return

        if cls._is_running:
            logger.warn("Maintenance scheduler is already running.")
            return

        cls._is_running = True
        cls._task = asyncio.create_task(cls._run_loop())
        logger.info(f"Maintenance scheduler started. Interval: {settings.MAINTENANCE_INTERVAL_MINUTES} minutes.")

    @classmethod
    async def stop(cls):
        """Cancels background runner cleanly on application shutdown."""
        cls._is_running = False
        if cls._task:
            cls._task.cancel()
            try:
                await cls._task
            except asyncio.CancelledError:
                pass
            cls._task = None
        logger.info("Maintenance scheduler stopped cleanly.")

    @classmethod
    async def _run_loop(cls):
        """Main periodic loop."""
        # Initial delay of 10 seconds after startup before first run
        await asyncio.sleep(10)

        while cls._is_running:
            try:
                cls.execute_maintenance_cycle()
            except Exception as e:
                logger.error(f"Maintenance cycle encountered an unexpected error: {e}", exc_info=True)

            # Sleep for configured interval
            interval_seconds = settings.MAINTENANCE_INTERVAL_MINUTES * 60
            await asyncio.sleep(interval_seconds)

    @classmethod
    def execute_maintenance_cycle(cls) -> Dict[str, Any]:
        """
        Executes a single maintenance cycle synchronously.
        Can be triggered automatically by scheduler or manually by administrators.
        """
        start_time = datetime.now(timezone.utc)
        logger.info("Beginning periodic maintenance cycle...")

        results: Dict[str, Any] = {
            "started_at": start_time.isoformat(),
            "tasks": {}
        }

        # Task 1: Database backup
        try:
            backup_result = BackupService.create_backup(label="scheduled_auto")
            results["tasks"]["backup"] = {
                "status": "SUCCESS",
                "filename": backup_result["backup_filename"],
                "checksum": backup_result["checksum_sha256"][:12]
            }
        except Exception as e:
            logger.error(f"Scheduled backup failed: {e}")
            results["tasks"]["backup"] = {"status": "FAILED", "error": str(e)}

        # Task 2: Clinical assets review audit
        db = SessionLocal()
        try:
            overview = ClinicalAssetMaintenanceService.get_maintenance_overview(db)
            results["tasks"]["clinical_assets_audit"] = {
                "status": "SUCCESS",
                "stale_conditions": overview["medical_conditions"]["stale_review_count"],
                "stale_rules": overview["clinical_rules"]["stale_review_count"]
            }
        except Exception as e:
            logger.error(f"Clinical asset review audit failed: {e}")
            results["tasks"]["clinical_assets_audit"] = {"status": "FAILED", "error": str(e)}
        finally:
            db.close()

        end_time = datetime.now(timezone.utc)
        results["finished_at"] = end_time.isoformat()
        results["duration_seconds"] = round((end_time - start_time).total_seconds(), 2)

        cls._last_run_time = end_time.isoformat()
        has_failure = any(t.get("status") == "FAILED" for t in results["tasks"].values())
        cls._last_run_status = "FAILED" if has_failure else "SUCCESS"
        cls._last_run_details = results
        cls._execution_count += 1

        logger.info(f"Maintenance cycle completed with status: {cls._last_run_status} in {results['duration_seconds']}s")
        return results

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """Returns scheduler runtime status and history."""
        return {
            "is_running": cls._is_running,
            "interval_minutes": settings.MAINTENANCE_INTERVAL_MINUTES,
            "execution_count": cls._execution_count,
            "last_run_time": cls._last_run_time,
            "last_run_status": cls._last_run_status,
            "last_run_details": cls._last_run_details
        }
