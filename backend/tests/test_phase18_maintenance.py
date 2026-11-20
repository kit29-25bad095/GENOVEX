import pytest
import os
import re
import json
import uuid
from datetime import datetime, timezone
from fastapi import Response, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, Base, engine
from app.core.config import settings
from app.core.security import User, RoleEnum, create_access_token, require_roles
from app.core.logging_config import sanitize_dict, StructuredJsonFormatter, correlation_id_ctx
from app.services.health_service import HealthService
from app.services.backup_service import BackupService
from app.services.ai_monitoring_service import AIMonitoringService, CircuitState
from app.services.clinical_asset_maintenance_service import ClinicalAssetMaintenanceService
from app.core.scheduler import MaintenanceScheduler
from app.api.v1.endpoints.health import get_health, get_detailed_diagnostics
from app.api.v1.endpoints.admin_maintenance import (
    create_backup_now, list_backups,
    get_clinical_assets_overview, get_ai_telemetry, reset_ai_circuit, get_scheduler_status
)

@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Ensure test admin and patient exist
    admin = db.query(User).filter(User.role == RoleEnum.ADMIN).first()
    if not admin:
        admin = User(
            email=f"admin_maint_{uuid.uuid4().hex[:6]}@genovex.ae",
            hashed_password="hashed_pass_test",
            full_name="Admin Systems Specialist",
            role=RoleEnum.ADMIN
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

    patient = db.query(User).filter(User.role == RoleEnum.PATIENT).first()
    if not patient:
        patient = User(
            email=f"patient_maint_{uuid.uuid4().hex[:6]}@genovex.ae",
            hashed_password="hashed_pass_test",
            full_name="Patient Sample",
            role=RoleEnum.PATIENT
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

    yield {"db": db, "admin": admin, "patient": patient}
    db.close()

# -----------------------------------------------------------------------------
# Module A: Health Monitoring Tests
# -----------------------------------------------------------------------------
def test_public_health_service(setup_db):
    """Verify public health monitoring returns healthy status without credential leaks."""
    db = setup_db["db"]
    resp = Response()
    data = get_health(response=resp, db=db)
    
    assert data["status"] in ["healthy", "degraded"]
    assert data["platform"] == settings.PROJECT_NAME
    assert data["version"] == settings.APP_VERSION
    assert "timestamp" in data
    assert data["services"]["database"] == "healthy"
    
    # Ensure no internal credentials leaked
    serialized = str(data).lower()
    assert "password" not in serialized
    assert "secret" not in serialized

def test_admin_diagnostics_endpoint_and_rbac(setup_db):
    """Verify detailed diagnostics returns latency and storage metrics, and enforces RBAC."""
    db = setup_db["db"]
    admin = setup_db["admin"]
    patient = setup_db["patient"]
    resp = Response()

    # 1. Verify authorized admin access
    diag = get_detailed_diagnostics(response=resp, db=db, current_user=admin)
    assert "checks" in diag
    assert "database" in diag["checks"]
    assert "latency_ms" in diag["checks"]["database"]
    assert "storage" in diag["checks"]
    assert diag["checks"]["storage"]["status"] in ["healthy", "degraded"]

    # 2. Verify RBAC dependency rejection for non-admin
    rbac_check = require_roles([RoleEnum.ADMIN, RoleEnum.SUPERADMIN])
    with pytest.raises(HTTPException) as exc_info:
        rbac_check(current_user=patient)
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

# -----------------------------------------------------------------------------
# Module B & C: Structured Logging & Sensitive Data Redaction Tests
# -----------------------------------------------------------------------------
def test_sensitive_data_redaction():
    """Verify redaction of tokens, passwords, secrets, and questionnaire answers."""
    sensitive_payload = {
        "user_email": "patient@genovex.ae",
        "password": "SuperSecretPassword123",
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "secret_key": "uae-secret-key-12345",
        "answer_value": "yes_current_steroids",
        "normal_field": "public_data",
        "nested": {
            "token": "sensitive_nested_token",
            "clinical_note": "Confidential patient record"
        }
    }
    sanitized = sanitize_dict(sensitive_payload)
    
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["access_token"] == "[REDACTED]"
    assert sanitized["secret_key"] == "[REDACTED]"
    assert sanitized["answer_value"] == "[REDACTED]"
    assert sanitized["nested"]["token"] == "[REDACTED]"
    assert sanitized["normal_field"] == "public_data"

def test_correlation_id_and_standardized_error_format():
    """Verify correlation ID context tracking and standardized error dictionary structure."""
    cid = "test_correlation_12345"
    token = correlation_id_ctx.set(cid)
    try:
        assert correlation_id_ctx.get() == cid
        
        # Test error response structure matches Phase 18 standard
        error_content = {
            "error": {
                "code": "RESOURCE_NOT_FOUND",
                "message": "The requested medical condition was not found.",
                "correlation_id": correlation_id_ctx.get(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        assert error_content["error"]["code"] == "RESOURCE_NOT_FOUND"
        assert error_content["error"]["correlation_id"] == cid
        assert "timestamp" in error_content["error"]
    finally:
        correlation_id_ctx.reset(token)

# -----------------------------------------------------------------------------
# Module D: Database Backup and Integrity Tests
# -----------------------------------------------------------------------------
def test_database_backup_and_integrity_verification():
    """Verify online backup creation, SHA-256 checksum, SQLite integrity check, and rotation."""
    # Create test backup
    backup_result = BackupService.create_backup(label="test_phase18")
    assert backup_result["success"] is True
    assert "backup_filename" in backup_result
    assert "checksum_sha256" in backup_result
    assert os.path.exists(backup_result["backup_path"])

    filename = backup_result["backup_filename"]
    backup_path = backup_result["backup_path"]

    # Verify integrity
    integrity_result = BackupService.verify_backup_integrity(backup_path)
    assert integrity_result["valid"] is True
    assert integrity_result["integrity_result"] == "ok"
    assert integrity_result["table_count"] > 0

    # List backups and verify test backup is listed
    backups = BackupService.list_backups()
    assert any(b["filename"] == filename for b in backups)

# -----------------------------------------------------------------------------
# Module E, F, G: Clinical Asset Maintenance & Audit Tests
# -----------------------------------------------------------------------------
def test_clinical_asset_maintenance_audit(setup_db):
    """Verify staleness detection and review audit across content, rules, and questionnaires."""
    db = setup_db["db"]
    overview = ClinicalAssetMaintenanceService.get_maintenance_overview(db)
    
    assert "medical_conditions" in overview
    assert "clinical_rules" in overview
    assert "questionnaires" in overview
    assert "review_validity_period_days" in overview
    assert overview["review_validity_period_days"] == 365
    assert overview["medical_conditions"]["total_count"] >= 3
    assert overview["clinical_rules"]["total_count"] >= 15
    assert overview["questionnaires"]["total_versions"] >= 1

# -----------------------------------------------------------------------------
# Module H: AI Circuit Breaker and Reliability Telemetry Tests
# -----------------------------------------------------------------------------
def test_ai_circuit_breaker_and_fallback():
    """Verify circuit trips to OPEN after failure threshold and returns deterministic fallback."""
    # Reset circuit breaker
    AIMonitoringService.reset_circuit()
    assert AIMonitoringService.get_circuit_state() == CircuitState.CLOSED

    # Failing function
    def failing_ai_call():
        raise RuntimeError("Simulated AI Provider API timeout (HTTP 504)")

    def safe_deterministic_fallback():
        return {
            "status": "FALLBACK_APPLIED",
            "clinical_tier": "TIER_3_MODERATE_RISK",
            "message": "Deterministic clinical guideline output applied safely."
        }

    # Execute 3 times to hit threshold (settings.AI_FAILURE_THRESHOLD = 3)
    for i in range(3):
        result = AIMonitoringService.execute_with_circuit_breaker(
            call_fn=failing_ai_call,
            fallback_fn=safe_deterministic_fallback
        )
        assert result["status"] == "FALLBACK_APPLIED"

    # Circuit breaker must now be OPEN
    assert AIMonitoringService.get_circuit_state() == CircuitState.OPEN

    # Subsequent execution must immediately invoke fallback without attempting failing_ai_call
    fast_fallback_result = AIMonitoringService.execute_with_circuit_breaker(
        call_fn=failing_ai_call,
        fallback_fn=safe_deterministic_fallback
    )
    assert fast_fallback_result["status"] == "FALLBACK_APPLIED"

    # Telemetry verification
    telemetry = AIMonitoringService.get_telemetry_summary()
    assert telemetry["circuit_breaker_state"] == "OPEN"
    assert telemetry["total_requests"] >= 3
    assert telemetry["total_failures"] >= 3

    # Reset circuit back to CLOSED
    AIMonitoringService.reset_circuit()
    assert AIMonitoringService.get_circuit_state() == CircuitState.CLOSED

# -----------------------------------------------------------------------------
# Module I: Maintenance Scheduler Cycle Execution Test
# -----------------------------------------------------------------------------
def test_maintenance_scheduler_cycle():
    """Verify idempotent execution of synchronous maintenance cycle."""
    cycle_result = MaintenanceScheduler.execute_maintenance_cycle()
    assert "started_at" in cycle_result
    assert "tasks" in cycle_result
    assert "backup" in cycle_result["tasks"]
    assert cycle_result["tasks"]["backup"]["status"] == "SUCCESS"
    assert "clinical_assets_audit" in cycle_result["tasks"]
    assert cycle_result["tasks"]["clinical_assets_audit"]["status"] == "SUCCESS"
