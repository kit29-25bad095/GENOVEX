import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import sqlite3

from app.core.security import User, RoleEnum, get_password_hash, create_access_token
from main import app

client = TestClient(app)

@pytest.fixture
def auth_user(db: Session):
    u = db.query(User).filter(User.email == "p14_test_user@genovex.ae").first()
    if not u:
        u = User(
            email="p14_test_user@genovex.ae",
            hashed_password=get_password_hash("InitialPass123!"),
            full_name="P14 Test User",
            role=RoleEnum.PATIENT,
            is_active=True
        )
        db.add(u)
        db.commit()
        db.refresh(u)
    token = create_access_token(data={"sub": u.email, "role": u.role.value, "uid": u.id})
    return {"user": u, "token": token, "headers": {"Authorization": f"Bearer {token}"}}

def test_database_schema_complete_parity(db: Session):
    """
    AC01: Verifies that all 17 application tables exist without missing models,
    with zero foreign key violations or physical corruption.
    """
    conn = db.connection().connection
    cur = conn.cursor()

    cur.execute("PRAGMA integrity_check;")
    assert cur.fetchall() == [("ok",)]

    cur.execute("PRAGMA foreign_key_check;")
    assert cur.fetchall() == []

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [r[0] for r in cur.fetchall() if r[0] != "alembic_version"]
    assert len(tables) == 17

def test_user_profile_update_api(auth_user):
    """AC02: Verifies PUT /api/v1/auth/me updates user profile cleanly."""
    payload = {
        "full_name": "Updated P14 Name",
        "credentials_summary": "Updated Credentials"
    }
    res = client.put("/api/v1/auth/me", json=payload, headers=auth_user["headers"])
    assert res.status_code == 200
    data = res.json()
    assert data["full_name"] == "Updated P14 Name"
    assert data["credentials_summary"] == "Updated Credentials"

def test_change_password_api(auth_user):
    """AC03: Verifies POST /api/v1/auth/change-password enforces password policy and verifies old password."""
    # 1. Incorrect old password -> 400
    bad_old = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "WrongPassword!", "new_password": "NewSecretPass123!"},
        headers=auth_user["headers"]
    )
    assert bad_old.status_code == 400
    assert "incorrect" in bad_old.json()["detail"].lower()

    # 2. Short new password (< 8 chars) -> 400
    too_short = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "InitialPass123!", "new_password": "short"},
        headers=auth_user["headers"]
    )
    assert too_short.status_code == 400
    assert "at least 8 characters" in too_short.json()["detail"].lower()

    # 3. Successful change -> 200
    success = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "InitialPass123!", "new_password": "NewValidPassword123!"},
        headers=auth_user["headers"]
    )
    assert success.status_code == 200
    assert success.json()["status"] == "success"

def test_input_validation_rejection_standardized():
    """AC04: Verifies server-side schema input validation rejects malformed data with 422."""
    # Missing required email/password in registration
    res = client.post("/api/v1/auth/register", json={"invalid_field": "data"})
    assert res.status_code == 422
    assert "detail" in res.json()

def test_api_version_and_health_integration():
    """AC05: Verifies /health endpoint returns online status and correct UAE market module."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("online", "healthy")
    assert data["market"] == "UAE"
    assert data["version"] == "1.0.0"
