from typing import List, Dict, Any
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, User, RoleEnum
from app.services.backup_service import BackupService
from app.services.ai_monitoring_service import AIMonitoringService
from app.services.clinical_asset_maintenance_service import ClinicalAssetMaintenanceService
from app.core.scheduler import MaintenanceScheduler

router = APIRouter(prefix="/admin/maintenance", tags=["Admin Maintenance & Reliability"])

def verify_admin_access(user: User):
    if user.role not in [RoleEnum.ADMIN, RoleEnum.SUPERADMIN, RoleEnum.CLINICIAN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Administrative or Clinician privileges required."
        )

@router.get("/backups", summary="List database backups")
def list_backups(current_user: User = Depends(get_current_user)) -> List[Dict[str, Any]]:
    verify_admin_access(current_user)
    return BackupService.list_backups()

@router.post("/backups/create", status_code=status.HTTP_201_CREATED, summary="Trigger immediate database backup")
def create_backup_now(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    verify_admin_access(current_user)
    return BackupService.create_backup(label="manual_admin")

@router.get("/clinical-assets", summary="Clinical assets review and maintenance overview")
def get_clinical_assets_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    verify_admin_access(current_user)
    return ClinicalAssetMaintenanceService.get_maintenance_overview(db)

@router.get("/ai-telemetry", summary="Operational AI circuit breaker and latency metrics")
def get_ai_telemetry(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    verify_admin_access(current_user)
    return AIMonitoringService.get_telemetry_summary()

@router.post("/ai-telemetry/reset", summary="Reset AI circuit breaker")
def reset_ai_circuit(current_user: User = Depends(get_current_user)) -> Dict[str, str]:
    verify_admin_access(current_user)
    AIMonitoringService.reset_circuit()
    return {"message": "AI circuit breaker successfully reset to CLOSED"}

@router.get("/scheduler", summary="Maintenance scheduler status")
def get_scheduler_status(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    verify_admin_access(current_user)
    return MaintenanceScheduler.get_status()

@router.post("/scheduler/run-now", summary="Execute maintenance cycle immediately")
def run_maintenance_cycle_now(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    verify_admin_access(current_user)
    return MaintenanceScheduler.execute_maintenance_cycle()
