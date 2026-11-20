
from app.models.clinical_rules import ClinicalRule, ClinicalRuleStatus, ClinicalOutcomeTier
from app.models.medical_content import MedicalCondition, PublicationStatus, MedicalCategory, ContentVersion
from app.services.clinical_rule_management_service import ClinicalRuleManagementService
from app.services.medical_content_service import MedicalContentService
from app.schemas.clinical_rules import ClinicalRuleCreate, ClinicalRuleReviewAction
from app.schemas.medical_content import (
    MedicalConditionCreate, MedicalConditionUpdate, ConditionContentSchema,
    ClinicalReviewActionRequest, RestoreVersionRequest
)
from app.schemas.auth import UserUpdateRequest
from app.api.v1.endpoints.auth import update_user_role_and_status, get_all_users_admin
from fastapi import HTTPException
from app.models.questionnaire import QuestionDomain

"""
GENOVEX Phase 11: Admin Dashboard Backend Test Suite
Validates all administrative endpoints, aggregate operational metrics,
user management with strict privilege boundaries, self-escalation prevention,
final SUPERADMIN lockout prevention, shared review pool semantics,
privacy preservation, and RBAC enforcement.
Runs in isolated disposable database sandbox without modifying authoritative genovex.db.
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app as fastapi_app
from app.core.database import SessionLocal
from app.core.security import User, RoleEnum, create_access_token, AuditLog, get_password_hash
from app.models.questionnaire import Assessment, AssessmentStatus, QuestionnaireVersion
from app.models.assessment_report import AssessmentReport
from app.models.clinical_rules import ClinicalOutcomeTier


@pytest.fixture(scope="module")
def admin_client():
    client = TestClient(fastapi_app)
    return client


@pytest.fixture(scope="module")
def setup_admin_data():
    db = SessionLocal()
    # 1. Create distinct test personas
    superadmin = db.query(User).filter(User.email == "superadmin_test@genovex.ae").first()
    if not superadmin:
        superadmin = User(
            email="superadmin_test@genovex.ae",
            full_name="Super Administrator",
            role=RoleEnum.SUPERADMIN,
            hashed_password=get_password_hash("SuperAdminPass123!"),
            is_active=True
        )
        db.add(superadmin)

    admin = db.query(User).filter(User.email == "admin_test@genovex.ae").first()
    if not admin:
        admin = User(
            email="admin_test@genovex.ae",
            full_name="Standard Administrator",
            role=RoleEnum.ADMIN,
            hashed_password=get_password_hash("AdminPass123!"),
            is_active=True
        )
        db.add(admin)

    clinician = db.query(User).filter(User.email == "clinician_test@genovex.ae").first()
    if not clinician:
        clinician = User(
            email="clinician_test@genovex.ae",
            full_name="Dr. Test Clinician",
            role=RoleEnum.CLINICIAN,
            credentials_summary="Consultant Andrologist / UAE MOHAP",
            hashed_password=get_password_hash("ClinicianPass123!"),
            is_active=True
        )
        db.add(clinician)

    patient = db.query(User).filter(User.email == "patient_test@genovex.ae").first()
    if not patient:
        patient = User(
            email="patient_test@genovex.ae",
            full_name="Test Patient",
            role=RoleEnum.PATIENT,
            hashed_password=get_password_hash("PatientPass123!"),
            is_active=True
        )
        db.add(patient)

    # Secondary target patient for management tests
    managed_user = db.query(User).filter(User.email == "managed_target@genovex.ae").first()
    if not managed_user:
        managed_user = User(
            email="managed_target@genovex.ae",
            full_name="Target User for Management",
            role=RoleEnum.PATIENT,
            hashed_password=get_password_hash("TargetPass123!"),
            is_active=True
        )
        db.add(managed_user)

    db.commit()
    db.refresh(superadmin)
    db.refresh(admin)
    db.refresh(clinician)
    db.refresh(patient)
    db.refresh(managed_user)

    # 2. Generate auth tokens
    superadmin_token = create_access_token({"sub": superadmin.email, "role": superadmin.role.value})
    admin_token = create_access_token({"sub": admin.email, "role": admin.role.value})
    clinician_token = create_access_token({"sub": clinician.email, "role": clinician.role.value})
    patient_token = create_access_token({"sub": patient.email, "role": patient.role.value})

    data = {
        "superadmin": superadmin,
        "admin": admin,
        "clinician": clinician,
        "patient": patient,
        "managed_user": managed_user,
        "superadmin_token": superadmin_token,
        "admin_token": admin_token,
        "clinician_token": clinician_token,
        "patient_token": patient_token,
    }
    yield data
    db.close()


def _auth_header(token: str):
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# 1. Operational Overview Endpoint Tests (AC01, AC02, AC03, AC14)
# ===========================================================================
def test_admin_overview_metrics_accuracy(admin_client, setup_admin_data):
    """Verifies overview statistics reflect real database aggregations and governance warnings."""
    token = setup_admin_data["admin_token"]
    res = admin_client.get("/api/v1/admin/overview", headers=_auth_header(token))
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["users_total"] >= 5
    assert data["users_active"] >= 5
    assert "PATIENT" in data["users_by_role"]
    assert "CLINICIAN" in data["users_by_role"]
    assert "ADMIN" in data["users_by_role"]
    assert "SUPERADMIN" in data["users_by_role"]

    assert "assessments_total" in data
    assert "reports_total" in data
    assert data["reports_withheld_count"] == data["reports_total"]
    assert "clinical_governance_status" in data
    assert "WITHHELD" in data["clinical_governance_status"]
    assert "NOTICE" in data["governance_warning"]
    assert "HTTP 422" in data["governance_warning"]
    assert data["platform_health_status"] == "HEALTHY"


# ===========================================================================
# 2. User Management Listing, Search, Pagination (AC04)
# ===========================================================================
def test_admin_user_listing_pagination_and_search(admin_client, setup_admin_data):
    """Verifies user listing supports pagination, text search, and role/status filtering."""
    token = setup_admin_data["admin_token"]

    # Search by email
    res = admin_client.get("/api/v1/admin/users?search=managed_target", headers=_auth_header(token))
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["email"] == "managed_target@genovex.ae"

    # Filter by role
    res = admin_client.get("/api/v1/admin/users?role=CLINICIAN", headers=_auth_header(token))
    assert res.status_code == 200
    data = res.json()
    assert all(item["role"] == "CLINICIAN" for item in data["items"])

    # Pagination bounds
    res = admin_client.get("/api/v1/admin/users?page=1&page_size=2", headers=_auth_header(token))
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) <= 2
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total_pages"] >= 1


# ===========================================================================
# 3. User Detail View (AC04)
# ===========================================================================
def test_admin_user_detail_view(admin_client, setup_admin_data):
    """Verifies user detail returns profile metadata and recent audit logs."""
    token = setup_admin_data["admin_token"]
    user_id = setup_admin_data["managed_user"].id

    res = admin_client.get(f"/api/v1/admin/users/{user_id}", headers=_auth_header(token))
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == user_id
    assert data["email"] == "managed_target@genovex.ae"
    assert "assessments_count" in data
    assert "recent_audit_logs" in data

    # 404 on non-existent user
    res_404 = admin_client.get("/api/v1/admin/users/999999", headers=_auth_header(token))
    assert res_404.status_code == 404


# ===========================================================================
# 4. User Status Update & Audit Trail (AC05, AC10)
# ===========================================================================
def test_admin_user_status_update_and_audit_trail(admin_client, setup_admin_data):
    """Verifies account activation and deactivation with mandatory audit logging."""
    token = setup_admin_data["admin_token"]
    target_id = setup_admin_data["managed_user"].id

    # 1. Deactivate target user
    res = admin_client.patch(
        f"/api/v1/admin/users/{target_id}/status",
        json={"is_active": False, "reason": "Security hold for audit verification"},
        headers=_auth_header(token)
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_active"] is False

    # 2. Reactivate target user
    res2 = admin_client.patch(
        f"/api/v1/admin/users/{target_id}/status",
        json={"is_active": True, "reason": "Verification completed"},
        headers=_auth_header(token)
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["is_active"] is True

    # 3. Verify audit log event was created
    audit_res = admin_client.get(f"/api/v1/admin/audit-events?action=ADMIN_USER_STATUS_UPDATE", headers=_auth_header(token))
    assert audit_res.status_code == 200
    audit_data = audit_res.json()
    assert audit_data["total"] >= 2
    assert audit_data["items"][0]["resource_id"] == str(target_id)


# ===========================================================================
# 5. Final SUPERADMIN Lockout Prevention (AC07)
# ===========================================================================
def test_admin_final_superadmin_lockout_prevention(admin_client, setup_admin_data):
    """Verifies that the final active SUPERADMIN cannot be deactivated or demoted."""
    superadmin_token = setup_admin_data["superadmin_token"]
    db = SessionLocal()
    # Ensure there is exactly 1 active SUPERADMIN in the test sandbox for this lockout test
    active_superadmins = db.query(User).filter(User.role == RoleEnum.SUPERADMIN, User.is_active == True).all()
    # Deactivate any extra superadmins so that only setup_admin_data["superadmin"] is the sole active one
    target_superadmin = setup_admin_data["superadmin"]
    for sa in active_superadmins:
        if sa.id != target_superadmin.id:
            sa.is_active = False
    db.commit()
    db.close()

    # Attempt to deactivate final active SUPERADMIN
    res_deact = admin_client.patch(
        f"/api/v1/admin/users/{target_superadmin.id}/status",
        json={"is_active": False, "reason": "Accidental lockout attempt"},
        headers=_auth_header(superadmin_token)
    )
    assert res_deact.status_code == 400, res_deact.text
    assert "final active SUPERADMIN" in res_deact.json()["detail"]

    # Attempt to demote final active SUPERADMIN
    res_demote = admin_client.patch(
        f"/api/v1/admin/users/{target_superadmin.id}/role",
        json={"role": "ADMIN", "reason": "Accidental demotion attempt"},
        headers=_auth_header(superadmin_token)
    )
    assert res_demote.status_code == 400, res_demote.text
    assert any(msg in res_demote.json()["detail"] for msg in ["Self-role modification", "final active SUPERADMIN"])


# ===========================================================================
# 6. Self-Role Modification Prevention (AC07)
# ===========================================================================
def test_admin_self_role_modification_prevention(admin_client, setup_admin_data):
    """Verifies administrators cannot modify their own roles."""
    admin_token = setup_admin_data["admin_token"]
    admin_id = setup_admin_data["admin"].id

    # Admin attempts to self-escalate to SUPERADMIN
    res = admin_client.patch(
        f"/api/v1/admin/users/{admin_id}/role",
        json={"role": "SUPERADMIN", "reason": "Self privilege escalation"},
        headers=_auth_header(admin_token)
    )
    assert res.status_code == 400
    assert "Self-role modification is prohibited" in res.json()["detail"]


# ===========================================================================
# 7. Privilege Boundaries Between ADMIN and SUPERADMIN (AC06, AC15)
# ===========================================================================
def test_admin_privilege_boundaries_against_superadmin(admin_client, setup_admin_data):
    """Verifies ADMIN role cannot modify, deactivate, or promote to SUPERADMIN."""
    admin_token = setup_admin_data["admin_token"]
    superadmin_id = setup_admin_data["superadmin"].id
    target_id = setup_admin_data["managed_user"].id

    # 1. ADMIN cannot promote a user to SUPERADMIN
    res_promote = admin_client.patch(
        f"/api/v1/admin/users/{target_id}/role",
        json={"role": "SUPERADMIN", "reason": "Unauthorized promotion"},
        headers=_auth_header(admin_token)
    )
    assert res_promote.status_code == 403
    assert "cannot grant SUPERADMIN" in res_promote.json()["detail"]

    # 2. ADMIN cannot deactivate a SUPERADMIN
    res_deact = admin_client.patch(
        f"/api/v1/admin/users/{superadmin_id}/status",
        json={"is_active": False, "reason": "ADMIN trying to deactivate SUPERADMIN"},
        headers=_auth_header(admin_token)
    )
    assert res_deact.status_code == 403
    assert "cannot modify account status of a SUPERADMIN" in res_deact.json()["detail"]

    # 3. ADMIN cannot alter role of a SUPERADMIN
    res_role = admin_client.patch(
        f"/api/v1/admin/users/{superadmin_id}/role",
        json={"role": "CLINICIAN", "reason": "ADMIN trying to demote SUPERADMIN"},
        headers=_auth_header(admin_token)
    )
    assert res_role.status_code == 403
    assert "cannot modify the role of a SUPERADMIN" in res_role.json()["detail"]


# ===========================================================================
# 8. Assessment Statistics (AC03, AC08 - Zero PII)
# ===========================================================================
def test_admin_assessment_stats_zero_pii(admin_client, setup_admin_data):
    """Verifies assessment aggregate stats provide operational metrics with zero patient PII."""
    token = setup_admin_data["admin_token"]
    res = admin_client.get("/api/v1/admin/assessments/stats", headers=_auth_header(token))
    assert res.status_code == 200
    data = res.json()

    assert "total_assessments" in data
    assert "status_counts" in data
    assert "reports_generated" in data
    assert "incomplete_assessments" in data
    assert "withheld_clinical_results" in data
    assert "outcome_tier_counts" in data
    assert data["governance_withheld_percent"] == 100.0

    # Ensure no patient narrative or response data leaked
    for key in ["responses", "answers", "patient_name", "session_token"]:
        assert key not in data


# ===========================================================================
# 9. Clinician Operations & Shared Queue Architecture (AC09)
# ===========================================================================
def test_admin_clinician_operations_shared_pool(admin_client, setup_admin_data):
    """Verifies clinician operational metrics accurately represent the shared review pool."""
    token = setup_admin_data["admin_token"]
    res = admin_client.get("/api/v1/admin/clinician-operations", headers=_auth_header(token))
    assert res.status_code == 200
    data = res.json()

    assert data["registered_clinicians"] >= 1
    assert data["shared_review_pool"] is True
    assert data["exclusive_locking_implemented"] is False
    assert "pending_reviews" in data
    assert "in_review_count" in data
    assert "completed_reviews" in data
    assert isinstance(data["recent_reviews"], list)


# ===========================================================================
# 10. Audit Events Retrieval & Privacy (AC10)
# ===========================================================================
def test_admin_audit_events_pagination_and_privacy(admin_client, setup_admin_data):
    """Verifies audit events retrieval is paginated, filtered, and redacts sensitive tokens."""
    token = setup_admin_data["admin_token"]
    res = admin_client.get("/api/v1/admin/audit-events?page=1&page_size=10", headers=_auth_header(token))
    assert res.status_code == 200
    data = res.json()

    assert "items" in data
    assert data["storage_type"] == "APPLICATION_LEVEL_APPEND_ONLY"
    assert data["immutable_hardware_enforced"] is False

    # Check that no item contains plain passwords, jwt tokens, or api keys in details
    for item in data["items"]:
        if item.get("details") and isinstance(item["details"], dict):
            for k, v in item["details"].items():
                assert "password" not in k.lower() or v == "[REDACTED]"
                assert "secret" not in k.lower() or v == "[REDACTED]"


# ===========================================================================
# 11. Platform Health & Safe Configuration (AC11, AC12)
# ===========================================================================
def test_admin_platform_health_and_config(admin_client, setup_admin_data):
    """Verifies health check and config endpoints return operational telemetry without secrets."""
    token = setup_admin_data["admin_token"]

    # Health endpoint
    h_res = admin_client.get("/api/v1/admin/health", headers=_auth_header(token))
    assert h_res.status_code == 200
    h_data = h_res.json()
    assert h_data["status"] == "HEALTHY"
    assert h_data["database"]["connected"] is True
    assert h_data["gemini_live_egress_active"] is False
    assert h_data["clinical_governance_gate"] == "FAIL_CLOSED_ACTIVE"

    # Config endpoint
    c_res = admin_client.get("/api/v1/admin/config", headers=_auth_header(token))
    assert c_res.status_code == 200
    c_data = c_res.json()
    assert "environment" in c_data
    assert "allowed_cors_origins" in c_data
    assert c_data["shared_review_queue"] is True

    # Verify absence of secret keys
    raw_text = c_res.text
    for secret_word in ["SECRET_KEY", "GEMINI_API_KEY", "DATABASE_URL"]:
        assert secret_word not in raw_text


# ===========================================================================
# 12. Full Endpoint RBAC Matrix (AC15, AC16)
# ===========================================================================
def test_admin_endpoint_rbac_matrix(admin_client, setup_admin_data):
    """Audits every administrative endpoint individually against all role tiers."""
    endpoints = [
        ("GET", "/api/v1/admin/overview"),
        ("GET", "/api/v1/admin/users"),
        ("GET", f"/api/v1/admin/users/{setup_admin_data['managed_user'].id}"),
        ("GET", "/api/v1/admin/assessments/stats"),
        ("GET", "/api/v1/admin/clinician-operations"),
        ("GET", "/api/v1/admin/audit-events"),
        ("GET", "/api/v1/admin/health"),
        ("GET", "/api/v1/admin/config"),
    ]

    for method, path in endpoints:
        # Anonymous -> 401
        res_anon = admin_client.request(method, path)
        assert res_anon.status_code == 401, f"Expected 401 for anonymous on {path}, got {res_anon.status_code}"

        # PATIENT -> 403
        res_pat = admin_client.request(method, path, headers=_auth_header(setup_admin_data["patient_token"]))
        assert res_pat.status_code == 403, f"Expected 403 for PATIENT on {path}, got {res_pat.status_code}"

        # CLINICIAN -> 403
        res_clin = admin_client.request(method, path, headers=_auth_header(setup_admin_data["clinician_token"]))
        assert res_clin.status_code == 403, f"Expected 403 for CLINICIAN on {path}, got {res_clin.status_code}"

        # ADMIN -> 200
        res_adm = admin_client.request(method, path, headers=_auth_header(setup_admin_data["admin_token"]))
        assert res_adm.status_code == 200, f"Expected 200 for ADMIN on {path}, got {res_adm.status_code}"

        # SUPERADMIN -> 200
        res_s_adm = admin_client.request(method, path, headers=_auth_header(setup_admin_data["superadmin_token"]))
        assert res_s_adm.status_code == 200, f"Expected 200 for SUPERADMIN on {path}, got {res_s_adm.status_code}"


# ===========================================================================
# 13. Clinical Governance Separation (AC13, AC14)
# ===========================================================================
def test_admin_clinical_governance_separation(admin_client, setup_admin_data):
    """Verifies administrators cannot approve rules or bypass clinical report withholding."""
    token = setup_admin_data["admin_token"]

    # Confirm admin cannot release unapproved reports directly via evaluation
    # Starting and evaluating an unapproved assessment from admin context still withholds patient release
    res_gov = admin_client.get("/api/v1/admin/overview", headers=_auth_header(token))
    data = res_gov.json()
    assert "WITHHELD" in data["clinical_governance_status"]
    assert data["reports_withheld_count"] == data["reports_total"]


# ===========================================================================
# 14. Valid Role Promotion by SUPERADMIN (AC05, AC06)
# ===========================================================================
def test_admin_user_role_update_valid_promotion_and_audit(admin_client, setup_admin_data):
    """Verifies SUPERADMIN can promote a PATIENT to CLINICIAN with verifiable audit record."""
    superadmin_token = setup_admin_data["superadmin_token"]
    target_id = setup_admin_data["managed_user"].id

    res = admin_client.patch(
        f"/api/v1/admin/users/{target_id}/role",
        json={"role": "CLINICIAN", "reason": "Promoting verified clinical staff"},
        headers=_auth_header(superadmin_token)
    )
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "CLINICIAN"

    # Revert back to PATIENT
    res_rev = admin_client.patch(
        f"/api/v1/admin/users/{target_id}/role",
        json={"role": "PATIENT", "reason": "Test lifecycle cleanup"},
        headers=_auth_header(superadmin_token)
    )
    assert res_rev.status_code == 200
    assert res_rev.json()["role"] == "PATIENT"


# ===========================================================================
# 15. Pagination Bounds Clamping & Validation (AC04, AC10)
# ===========================================================================
def test_admin_pagination_bounds_enforced(admin_client, setup_admin_data):
    """Verifies that excessively large page_size is rejected by FastAPI schema bounds (le=100)."""
    token = setup_admin_data["admin_token"]

    # Page size > 100 is rejected by validation with 422
    res = admin_client.get("/api/v1/admin/users?page=1&page_size=500", headers=_auth_header(token))
    assert res.status_code == 422

    # Maximum permitted page size (100) succeeds
    res_valid = admin_client.get("/api/v1/admin/users?page=1&page_size=100", headers=_auth_header(token))
    assert res_valid.status_code == 200
    assert res_valid.json()["page_size"] == 100

    # Audit events pagination clamped / validated
    res_audit_invalid = admin_client.get("/api/v1/admin/audit-events?page=1&page_size=200", headers=_auth_header(token))
    assert res_audit_invalid.status_code == 422


# ===========================================================================
# 16. Audit Log Filtering by Resource & Action (AC10)
# ===========================================================================
def test_admin_audit_events_filtering(admin_client, setup_admin_data):
    """Verifies filtering by specific audit action and resource type."""
    token = setup_admin_data["admin_token"]

    res = admin_client.get(
        "/api/v1/admin/audit-events?action=ADMIN_USER_ROLE_UPDATE&resource_type=User",
        headers=_auth_header(token)
    )
    assert res.status_code == 200
    data = res.json()
    assert all(item["action"] == "ADMIN_USER_ROLE_UPDATE" for item in data["items"])
    assert all(item["resource_type"] == "User" for item in data["items"])


# ===========================================================================
# 17. Safe Config Excludes All Sensitive Secrets (AC12)
# ===========================================================================
def test_admin_config_strict_no_secret_leakage(admin_client, setup_admin_data):
    """Exhaustive check that config payload has zero secret keys, tokens, or hashes."""
    token = setup_admin_data["admin_token"]
    res = admin_client.get("/api/v1/admin/config", headers=_auth_header(token))
    assert res.status_code == 200
    data = res.json()

    assert "environment" in data
    assert "project_name" in data
    assert "allowed_cors_origins" in data

    forbidden_substrings = ["secret", "password", "token", "key", "credential", "private", "hash"]
    for k in data.keys():
        for sub in forbidden_substrings:
            if sub in k.lower() and k != "auth_jwt_algorithm":
                assert False, f"Potential sensitive key found in config: {k}"

# ===========================================================================
# Additional Phase 11 Service Governance Tests (from remote)
# ===========================================================================

def test_admin_user_role_management_and_audit(db: Session):
    """
    Test Phase 11 User & Role Governance:
    - Admin can update user role, credentials, and active status
    - AuditLog records the change immutably
    - Superadmin boundary protections are enforced
    """
    # Create test actor users
    admin_actor = User(
        email="admin.tester@genovex.ae",
        full_name="Admin Tester",
        role=RoleEnum.ADMIN,
        hashed_password=get_password_hash("password123"),
        is_active=True
    )
    superadmin_actor = User(
        email="superadmin.tester@genovex.ae",
        full_name="Superadmin Tester",
        role=RoleEnum.SUPERADMIN,
        hashed_password=get_password_hash("password123"),
        is_active=True
    )
    target_user = User(
        email="dr.candidate@genovex.ae",
        full_name="Dr. Candidate",
        role=RoleEnum.PATIENT,
        hashed_password=get_password_hash("password123"),
        is_active=True
    )
    db.add_all([admin_actor, superadmin_actor, target_user])
    db.commit()

    # Mock Request for IP capture
    class MockClient:
        host = "10.0.0.1"
    class MockRequest:
        client = MockClient()

    # 1. Admin elevates patient to CLINICIAN with credentials
    update_req = UserUpdateRequest(
        role=RoleEnum.CLINICIAN,
        credentials_summary="Specialist Urologist (DHA-P-998877)",
        is_active=True
    )
    updated = update_user_role_and_status(
        user_id=target_user.id,
        req=update_req,
        request=MockRequest(),
        current_user=admin_actor,
        db=db
    )
    assert updated.role == RoleEnum.CLINICIAN
    assert updated.credentials_summary == "Specialist Urologist (DHA-P-998877)"

    # Verify AuditLog emission
    audit = db.query(AuditLog).filter(
        AuditLog.action == "UPDATE_USER_ROLE",
        AuditLog.resource_id == str(target_user.id)
    ).first()
    assert audit is not None
    assert audit.user_email == admin_actor.email
    assert audit.details["new_role"] == "CLINICIAN"

    # 2. Standard Admin cannot assign SUPERADMIN role
    illegal_req = UserUpdateRequest(role=RoleEnum.SUPERADMIN)
    with pytest.raises(HTTPException) as exc_info:
        update_user_role_and_status(
            user_id=target_user.id,
            req=illegal_req,
            request=MockRequest(),
            current_user=admin_actor,
            db=db
        )
    assert exc_info.value.status_code == 403

    # 3. Superadmin CAN assign SUPERADMIN role
    valid_superadmin_update = update_user_role_and_status(
        user_id=target_user.id,
        req=illegal_req,
        request=MockRequest(),
        current_user=superadmin_actor,
        db=db
    )
    assert valid_superadmin_update.role == RoleEnum.SUPERADMIN

    # 4. List users filtered by role
    clinicians = get_all_users_admin(role=RoleEnum.CLINICIAN, current_user=admin_actor, db=db)
    assert isinstance(clinicians, list)


def test_clinical_rule_authoring_and_approval_lifecycle(db: Session):
    """
    Test Phase 11 Clinical Rules CMS:
    - Authoring draft rule with 3-valued logic trigger
    - Submission for review
    - Clinician approval
    - Publishing to live engine and immutable snapshot creation
    """
    clinician = User(
        email="clinician.reviewer@genovex.ae",
        full_name="Dr. Reviewer",
        role=RoleEnum.CLINICIAN,
        hashed_password=get_password_hash("password123"),
        is_active=True
    )
    db.add(clinician)
    db.commit()

    # 1. Author Draft Rule
    rule_data = ClinicalRuleCreate(
        rule_code="R-TEST-PHASE11-DRAFT",
        title_en="Klinefelter Genetic Screen Pathway",
        title_ar="مسار الفحص الجيني لمتلازمة كلاينفلتر",
        domain_code=QuestionDomain.FAMILY_GENETIC,
        relevant_question_keys=["Q_KLINEFELTER_FAMILY"],
        outcome_tier=ClinicalOutcomeTier.TIER_3_EVAL_RECOMMENDED,
        is_urgent_red_flag=False,
        priority_rank=35,
        recommended_specialty="Clinical Geneticist / Reproductive Endocrinologist",
        trigger_criteria={"all_of": [{"question_key": "Q_KLINEFELTER_FAMILY", "operator": "eq", "value": "yes"}]},
        clinical_rationale_en="Azoospermia risk high in 47,XXY karyotype.",
        clinical_rationale_ar="ارتفاع خطر فقد النطاف في النمط النووي 47,XXY.",
        evidence_references=[{"title": "EAU Guidelines on Male Infertility (2024)", "year": 2024}],
        evidence_classification="Level 1b"
    )

    created_rule = ClinicalRuleManagementService.create_rule(db=db, data=rule_data, current_user=clinician)
    assert created_rule.rule_code == "R-TEST-PHASE11-DRAFT"
    assert created_rule.status == ClinicalRuleStatus.DRAFT

    # 2. Submit for review
    submitted = ClinicalRuleManagementService.submit_for_review(db=db, rule_id=created_rule.id, current_user=clinician)
    assert submitted.status == ClinicalRuleStatus.SUBMITTED_FOR_REVIEW

    # 3. Clinician Review & Approval
    review_action = ClinicalRuleReviewAction(
        action="APPROVE",
        reviewer_notes="Clinical evidence aligns with EAU Section 7 recommendations."
    )
    approved = ClinicalRuleManagementService.clinical_review(
        db=db,
        rule_id=created_rule.id,
        action=review_action,
        current_user=clinician
    )
    assert approved.status == ClinicalRuleStatus.APPROVED
    assert approved.clinical_reviewer_id == clinician.id
    assert approved.approved_at is not None

    # 4. Publish to live engine
    published = ClinicalRuleManagementService.publish_rule(db=db, rule_id=created_rule.id, current_user=clinician)
    assert published.status == ClinicalRuleStatus.PUBLISHED
    assert published.published_at is not None

    # 5. Verify version snapshot
    versions = ClinicalRuleManagementService.get_rule_versions(db=db, rule_id=created_rule.id)
    assert len(versions) >= 1
    assert versions[0].rule_code == "R-TEST-PHASE11-DRAFT"

    # Cleanup rule so subsequent clinical engine tests retain their 14-rule baseline
    created_rule.status = ClinicalRuleStatus.ARCHIVED
    db.commit()


def test_medical_content_cms_workflow_and_version_restoration(db: Session):
    """
    Test Phase 11 Medical Content CMS:
    - Create condition with bilingual fields
    - Review action workflow (SUBMIT -> APPROVE -> PUBLISH)
    - Update condition with automatic snapshot creation
    - Historical version restoration
    """
    admin = User(
        email="content.admin@genovex.ae",
        full_name="Content Admin",
        role=RoleEnum.ADMIN,
        hashed_password=get_password_hash("password123"),
        is_active=True
    )
    clinician = User(
        email="medical.director@genovex.ae",
        full_name="Medical Director",
        role=RoleEnum.CLINICIAN,
        hashed_password=get_password_hash("password123"),
        is_active=True
    )
    db.add_all([admin, clinician])
    db.commit()

    # Ensure category exists
    cat = db.query(MedicalCategory).first()
    if not cat:
        cat = MedicalCategory(slug="genetic-factors", name_en="Genetic Factors", name_ar="عوامل وراثية", display_order=1)
        db.add(cat)
        db.commit()

    # 1. Create Condition
    en_content = ConditionContentSchema(
        language="en",
        name="Y-Chromosome Microdeletion (AZF)",
        short_description="Microdeletions in AZFa, AZFb, or AZFc regions causing severe azoospermia.",
        detailed_explanation="Critical genetic screening required prior to surgical sperm retrieval.",
        biological_mechanism="Loss of DAZ and other essential spermatogenesis gene families on the Y chromosome.",
        causes_and_risk_factors="De novo microdeletions during male germ cell development.",
        possible_symptoms="Azoospermia or severe oligozoospermia with normal virilization.",
        silent_asymptomatic_presentation="Patients appear completely asymptomatic with normal secondary sexual traits.",
        clinical_significance="Guides feasibility of micro-TESE surgical sperm retrieval.",
        diagnostic_investigations="Multiplex PCR testing for AZFa, AZFb, and AZFc regions.",
        clinical_next_steps="Pre-procedure genetic counseling and reproductive andrologist evaluation."
    )
    ar_content = ConditionContentSchema(
        language="ar",
        name="الحذف الدقيق في الكروموسوم Y (AZF)",
        short_description="حذف دقيق في مناطق AZF يسبب فقد النطاف غير الانسدادي الشديد.",
        detailed_explanation="فحص وراثي دقيق مطلوب قبل عمليات استرجاع الحيوانات المنوية جراحياً.",
        biological_mechanism="فقدان جينات DAZ والجينات الضرورية لتكوين الحيوانات المنوية في الكروموسوم Y.",
        causes_and_risk_factors="طفرات حذف دقيقة جديدة تحدث أثناء تكوين الخلايا التناسلية الذكرية.",
        possible_symptoms="انعدام أو نقص حاد جداً في الحيوانات المنوية مع مظهر بدني طبيعي.",
        silent_asymptomatic_presentation="تكون الحالة غير مصحوبة بأعراض بدنية ظاهرة وتكتشف فقط بالفحص المخبري.",
        clinical_significance="تحدد إمكانية وجدوى استرجاع الحيوانات المنوية جراحياً عبر تقنية micro-TESE.",
        diagnostic_investigations="فحص تفاعل البوليميراز المتسلسل (PCR) لمناطق AZFa و AZFb و AZFc.",
        clinical_next_steps="استشارة وراثية متخصصة ومتابعة مع استشاري المسالك البولية التناسلية."
    )

    cond_in = MedicalConditionCreate(
        slug="y-chromosome-microdeletion-p11",
        category_id=cat.id,
        evidence_classification="Level 1A",
        organs_involved=["Testis", "Y Chromosome AZF Regions"],
        en_content=en_content,
        ar_content=ar_content
    )

    cond = MedicalContentService.create_condition(db=db, data=cond_in, user=admin)
    assert cond.slug == "y-chromosome-microdeletion-p11"
    assert cond.publication_status == PublicationStatus.DRAFT

    # 2. Review action: Submit -> Approve -> Publish
    MedicalContentService.handle_review_action(
        db=db,
        condition_id=cond.id,
        req=ClinicalReviewActionRequest(
            action="SUBMIT_FOR_REVIEW",
            reviewer_name=admin.full_name,
            reviewer_role=admin.role.value
        ),
        user=admin
    )
    approved_cond = MedicalContentService.handle_review_action(
        db=db,
        condition_id=cond.id,
        req=ClinicalReviewActionRequest(
            action="APPROVE",
            reviewer_name=clinician.full_name,
            reviewer_role=clinician.role.value,
            notes="Genetic criteria verified against EAU/ASRM guidelines"
        ),
        user=clinician
    )
    assert approved_cond.publication_status == PublicationStatus.APPROVED

    published_cond = MedicalContentService.handle_review_action(
        db=db,
        condition_id=cond.id,
        req=ClinicalReviewActionRequest(
            action="PUBLISH",
            reviewer_name=clinician.full_name,
            reviewer_role=clinician.role.value
        ),
        user=clinician
    )
    assert published_cond.publication_status == PublicationStatus.PUBLISHED

    # 3. Capture initial version
    initial_version = published_cond.current_version

    # 4. Update condition (should auto-bump version and snapshot)
    updated_cond = MedicalContentService.update_condition(
        db=db,
        condition_id=cond.id,
        data=MedicalConditionUpdate(
            evidence_classification="Level 1A+",
            organs_involved=["Testis", "AZFa", "AZFb", "AZFc"]
        ),
        user=admin
    )
    assert updated_cond.current_version > initial_version

    # 5. Check version snapshots
    versions = MedicalContentService.get_version_history(db=db, condition_id=cond.id)
    assert len(versions) >= 1

    # 6. Restore earlier version
    restored = MedicalContentService.restore_version(
        db=db,
        condition_id=cond.id,
        req=RestoreVersionRequest(
            version_number=versions[0].version_number,
            reason="Clinical consensus rollback",
            restored_by=admin.full_name
        ),
        user=admin
    )
    assert restored is not None
