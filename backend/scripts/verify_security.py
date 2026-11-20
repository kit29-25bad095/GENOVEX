import os
import sys
import json
from datetime import datetime, timezone

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, backend_path)

from app.core.config import settings
from app.core.security import User, RoleEnum, require_roles
from app.core.logging_config import sanitize_dict, StructuredJsonFormatter, correlation_id_ctx
from app.services.health_service import HealthService
from fastapi import Response, HTTPException, status

def run_security_verification():
    print("=== STEP 1: Verify Authentication & Authorization on Diagnostic Endpoints ===")
    # Test users
    admin_user = User(id=1, email="admin@genovex.ae", role=RoleEnum.ADMIN, is_active=True)
    superadmin_user = User(id=2, email="super@genovex.ae", role=RoleEnum.SUPERADMIN, is_active=True)
    clinician_user = User(id=3, email="dr.ali@genovex.ae", role=RoleEnum.CLINICIAN, is_active=True)
    patient_user = User(id=4, email="patient@genovex.ae", role=RoleEnum.PATIENT, is_active=True)

    # RBAC checker for diagnostics (ADMIN, SUPERADMIN, CLINICIAN)
    checker = require_roles([RoleEnum.ADMIN, RoleEnum.SUPERADMIN, RoleEnum.CLINICIAN])
    
    # 1. Admin allowed
    assert checker(admin_user) == admin_user
    print("[OK] ADMIN role authorized")
    
    # 2. Superadmin allowed
    assert checker(superadmin_user) == superadmin_user
    print("[OK] SUPERADMIN role authorized")
    
    # 3. Clinician allowed
    assert checker(clinician_user) == clinician_user
    print("[OK] CLINICIAN role authorized")
    
    # 4. Patient forbidden
    try:
        checker(patient_user)
        assert False, "PATIENT was erroneously allowed to access diagnostics!"
    except HTTPException as e:
        assert e.status_code == status.HTTP_403_FORBIDDEN
        print(f"[OK] PATIENT role rejected with 403 Forbidden: {e.detail}")

    print("\n=== STEP 2: Verify Diagnostic Endpoints Do Not Leak Infrastructure Secrets ===")
    public_health = HealthService.get_public_health()
    print("  Public health payload:", json.dumps(public_health))
    pub_str = str(public_health).lower()
    for forbidden in ["password", "secret", "token", "c:\\", "/users/", "database_url"]:
        assert forbidden not in pub_str, f"Forbidden infrastructure leakage: {forbidden} found in public health!"
    print("[OK] Zero infrastructure secrets leaked in public health endpoint!")

    print("\n=== STEP 3: Verify Sensitive Data Redaction in Deeply Nested Dictionaries ===")
    nested_payload = {
        "event": "user_assessment_submission",
        "user_email": "patient_uae@genovex.ae",
        "credentials": {
            "some_key": "some_val"
        },
        "auth_block": {
            "password": "ClearTextPassword123!",
            "token": "bearer eyJhbGciOi...",
            "api_key": "uae-secret-key-prod-9988",
            "access_token": "secret_access_token_val"
        },
        "clinical_data": {
            "session_token": "sess_abc123",
            "answer_value": "yes_current_use",
            "response_value_json": "cryptorchidism_surgery_at_age_4"
        },
        "benign_metadata": {
            "browser": "Chrome",
            "language": "ar-AE",
            "platform": "GENOVEX"
        }
    }

    sanitized = sanitize_dict(nested_payload)
    print("  Sanitized payload sample:")
    print("    credentials: ", sanitized["credentials"])
    print("    password:    ", sanitized["auth_block"]["password"])
    print("    token:       ", sanitized["auth_block"]["token"])
    print("    api_key:     ", sanitized["auth_block"]["api_key"])
    print("    answer_value:", sanitized["clinical_data"]["answer_value"])
    print("    browser:     ", sanitized["benign_metadata"]["browser"])

    # Assertions
    assert sanitized["credentials"] == "[REDACTED]"
    assert sanitized["auth_block"]["password"] == "[REDACTED]"
    assert sanitized["auth_block"]["token"] == "[REDACTED]"
    assert sanitized["auth_block"]["api_key"] == "[REDACTED]"
    assert sanitized["auth_block"]["access_token"] == "[REDACTED]"
    assert sanitized["clinical_data"]["answer_value"] == "[REDACTED]"
    assert sanitized["clinical_data"]["response_value_json"] == "[REDACTED]"
    assert sanitized["benign_metadata"]["browser"] == "Chrome"
    assert sanitized["benign_metadata"]["language"] == "ar-AE"
    print("[OK] All nested credentials, secrets, and clinical answers completely redacted!")

    print("\n=== STEP 4: Verify Structured JSON Log Redaction Formatting ===")
    formatter = StructuredJsonFormatter()
    import logging
    record = logging.LogRecord(
        name="genovex_security_test",
        level=logging.INFO,
        pathname=__file__,
        lineno=100,
        msg="Patient completed domain responses",
        args=(),
        exc_info=None
    )
    record.extra_fields = nested_payload
    
    log_line = formatter.format(record)
    log_dict = json.loads(log_line)
    
    assert log_dict["level"] == "INFO"
    assert log_dict["extra"]["auth_block"]["password"] == "[REDACTED]"
    assert "ClearTextPassword123!" not in log_line
    assert "yes_current_use" not in log_line
    print("[OK] Log record formatter pre-serialization sanitization verified!")

    print("\nALL SECURITY VERIFICATION CHECKS PASSED!")

if __name__ == "__main__":
    run_security_verification()
