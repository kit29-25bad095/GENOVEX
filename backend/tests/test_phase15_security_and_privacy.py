import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import User, RoleEnum, AuditLog, get_password_hash, verify_password, create_access_token
from main import app

client = TestClient(app)

@pytest.fixture
def privacy_users(db: Session):
    u = db.query(User).filter(User.email == "patient_p15@genovex.ae").first()
    if not u:
        u = User(
            email="patient_p15@genovex.ae",
            hashed_password=get_password_hash("PatientPass123!"),
            full_name="Privacy Test Patient",
            role=RoleEnum.PATIENT,
            is_active=True
        )
        db.add(u)
        db.commit()
        db.refresh(u)

    superadmin = db.query(User).filter(User.email == "superadmin_p15@genovex.ae").first()
    if not superadmin:
        superadmin = User(
            email="superadmin_p15@genovex.ae",
            hashed_password=get_password_hash("SuperPass123!"),
            full_name="Privacy SuperAdmin",
            role=RoleEnum.SUPERADMIN,
            is_active=True
        )
        db.add(superadmin)
        db.commit()
        db.refresh(superadmin)

    token_u = create_access_token(data={"sub": u.email, "role": u.role.value, "uid": u.id})
    token_sa = create_access_token(data={"sub": superadmin.email, "role": superadmin.role.value, "uid": superadmin.id})

    return {
        "user": u,
        "superadmin": superadmin,
        "headers_user": {"Authorization": f"Bearer {token_u}"},
        "headers_sa": {"Authorization": f"Bearer {token_sa}"}
    }

def test_export_personal_data_unauthorized():
    """AC01: Verifies that data export requires authentication."""
    res = client.get("/api/v1/auth/privacy/export-data")
    assert res.status_code == 401

def test_export_personal_data_compliance(privacy_users):
    """
    AC02: Verifies that user data export fulfills UAE PDPL / GDPR requirements,
    returning account profile, assessments, and regulatory attribution.
    """
    res = client.get("/api/v1/auth/privacy/export-data", headers=privacy_users["headers_user"])
    assert res.status_code == 200
    data = res.json()
    assert "export_timestamp" in data
    assert "user_profile" in data
    assert "assessments" in data
    assert data["user_profile"]["email"] == "patient_p15@genovex.ae"
    assert "UAE Federal Decree-Law No. 45" in data["regulatory_framework"]

def test_delete_account_workflow_and_anonymization(privacy_users, db: Session):
    """
    AC03: Verifies user account deletion and right-to-be-forgotten erasure workflow.
    Anonymizes email and full name, deactivates login, and writes compliance audit record.
    """
    u = privacy_users["user"]

    # Deletion without confirm -> 422/400
    res_bad = client.post("/api/v1/auth/privacy/delete-account?confirm=false", headers=privacy_users["headers_user"])
    assert res_bad.status_code == 400

    # Valid deletion
    res = client.post("/api/v1/auth/privacy/delete-account?confirm=true", headers=privacy_users["headers_user"])
    assert res.status_code == 200
    assert "permanently deactivated" in res.json()["message"]

    # Verify database state
    db.refresh(u)
    assert u.is_active is False
    assert "@redacted.local" in u.email
    assert u.full_name == "Redacted User"

    # Verify audit log recorded
    audit = db.query(AuditLog).filter(
        AuditLog.user_id == u.id,
        AuditLog.action == "USER_DATA_ERASURE"
    ).first()
    assert audit is not None
    assert audit.resource_type == "User"

def test_final_superadmin_deletion_lockout(privacy_users, db: Session):
    """
    AC04: Verifies that deletion of the last remaining active SuperAdmin is strictly blocked.
    """
    # Deactivate other superadmins so only 1 remains in sandbox
    sa = privacy_users["superadmin"]
    other_sas = db.query(User).filter(
        User.role == RoleEnum.SUPERADMIN,
        User.id != sa.id
    ).all()
    for o in other_sas:
        o.is_active = False
    db.commit()

    res = client.post("/api/v1/auth/privacy/delete-account?confirm=true", headers=privacy_users["headers_sa"])
    assert res.status_code == 400
    assert "last remaining active SuperAdmin" in res.json()["detail"]

def test_password_hashing_security():
    """AC05: Verifies that password hashing utilizes NIST-approved PBKDF2-SHA256 and verification."""
    raw = "MySecurePassword123!"
    hashed = get_password_hash(raw)
    assert hashed.startswith("$pbkdf2-sha256$")
    assert len(hashed) >= 50
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False
