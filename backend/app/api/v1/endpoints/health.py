from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.core.database import get_db
from app.services.health_service import HealthService
from app.core.security import get_current_user, User, RoleEnum

router = APIRouter(tags=["System Health & Diagnostics"])

@router.get("/health", summary="Public Application Health Check")
def get_health(response: Response, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Public health check endpoint for monitoring, uptime probes, and load balancers.
    Returns status: 'healthy', 'degraded', or 'unavailable'.
    Sets HTTP 503 if unavailable, HTTP 200 otherwise.
    """
    health = HealthService.get_public_health(db)
    if health["status"] == "unavailable":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return health

@router.get("/admin/health/diagnostics", summary="Detailed Health Diagnostics (Admin/Clinician Gated)")
def get_detailed_diagnostics(
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Detailed system diagnostics for authorized clinical operations & administrators.
    Reports database response latency, storage availability, and subsystem telemetry.
    """
    diagnostics = HealthService.get_detailed_diagnostics(db)
    if diagnostics["status"] == "unavailable":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return diagnostics
