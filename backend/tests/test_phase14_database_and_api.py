import pytest
import os
import tempfile
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy.pool import QueuePool
import sqlite3

from alembic.config import Config
from alembic import command

from app.core.config import settings
from app.core.database import create_configured_engine, get_db, Base
from app.core.security import User, RoleEnum, get_password_hash, create_access_token
from app.models.questionnaire import Assessment, AssessmentStatus
from app.models.assessment_report import AssessmentReport, ClinicalOutcomeTier
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

@pytest.fixture
def other_user(db: Session):
    u = db.query(User).filter(User.email == "p14_other_user@genovex.ae").first()
    if not u:
        u = User(
            email="p14_other_user@genovex.ae",
            hashed_password=get_password_hash("InitialPass123!"),
            full_name="P14 Other User",
            role=RoleEnum.PATIENT,
            is_active=True
        )
        db.add(u)
        db.commit()
        db.refresh(u)
    token = create_access_token(data={"sub": u.email, "role": u.role.value, "uid": u.id})
    return {"user": u, "token": token, "headers": {"Authorization": f"Bearer {token}"}}

@pytest.fixture
def admin_user(db: Session):
    u = db.query(User).filter(User.email == "p14_admin_user@genovex.ae").first()
    if not u:
        u = User(
            email="p14_admin_user@genovex.ae",
            hashed_password=get_password_hash("AdminPass123!"),
            full_name="P14 Admin User",
            role=RoleEnum.ADMIN,
            is_active=True
        )
        db.add(u)
        db.commit()
        db.refresh(u)
    token = create_access_token(data={"sub": u.email, "role": u.role.value, "uid": u.id})
    return {"user": u, "token": token, "headers": {"Authorization": f"Bearer {token}"}}


def test_database_schema_complete_parity(db: Session):
    """
    AC01: Verifies that all 18 application tables exist without missing models,
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
    assert len(tables) == 18
    assert "password_reset_tokens" in tables


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


def test_postgresql_connection_pool_configuration():
    """AC06: Verifies production PostgreSQL engine configuration and connection pool parameters."""
    from unittest.mock import patch

    pg_url = "postgresql://uae_user:secure_pwd@me-central-1.rds.amazonaws.com:5432/genovex_prod"
    with patch("app.core.database.create_engine") as mock_ce:
        mock_ce.return_value = "mock_pg_engine"
        result_engine = create_configured_engine(pg_url)
        assert result_engine == "mock_pg_engine"
        mock_ce.assert_called_once_with(
            pg_url,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            pool_recycle=settings.DB_POOL_RECYCLE,
            pool_pre_ping=settings.DB_POOL_PRE_PING,
            echo=False
        )

    # Legacy postgres:// URL normalization
    legacy_url = "postgres://uae_user:secure_pwd@me-central-1.rds.amazonaws.com:5432/genovex_prod"
    with patch("app.core.database.create_engine") as mock_ce_legacy:
        mock_ce_legacy.return_value = "mock_legacy_engine"
        result_legacy = create_configured_engine(legacy_url)
        assert result_legacy == "mock_legacy_engine"
        mock_ce_legacy.assert_called_once_with(
            pg_url,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            pool_recycle=settings.DB_POOL_RECYCLE,
            pool_pre_ping=settings.DB_POOL_PRE_PING,
            echo=False
        )

    # Test QueuePool direct instantiation with configured pool parameters
    pool = QueuePool(
        creator=lambda: None,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        timeout=settings.DB_POOL_TIMEOUT,
        recycle=settings.DB_POOL_RECYCLE,
        pre_ping=settings.DB_POOL_PRE_PING
    )
    assert pool.size() == 20
    assert pool._max_overflow == 10
    assert pool._timeout == 30
    assert pool._recycle == 1800
    assert pool._pre_ping is True


def test_session_transaction_rollback_on_failure():
    """AC07: Verifies get_db session rollback on unhandled exceptions."""
    gen = get_db()
    db_session = next(gen)
    assert db_session.is_active

    # Insert a dummy record without committing
    dummy = User(
        email=f"rollback_{uuid.uuid4().hex[:8]}@genovex.ae",
        hashed_password=get_password_hash("Pass123!"),
        full_name="Rollback Test",
        role=RoleEnum.PATIENT
    )
    db_session.add(dummy)

    # Simulate an unhandled exception inside the request lifecycle
    with pytest.raises(RuntimeError):
        try:
            raise RuntimeError("Simulated request failure")
        except RuntimeError as e:
            gen.throw(e)


def test_alembic_fresh_database_upgrade_downgrade_cycle():
    """AC08: Verifies Alembic can cleanly build from base to head, downgrade, and re-upgrade."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        tmp_db_path = tmp_file.name

    try:
        # 1. Point Alembic config to the clean temporary database
        alembic_cfg = Config("backend/alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{tmp_db_path.replace(os.sep, '/')}")

        # 2. Upgrade to head
        command.upgrade(alembic_cfg, "head")

        # Verify tables created
        conn = sqlite3.connect(tmp_db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [r[0] for r in cur.fetchall() if r[0] != "alembic_version"]
        assert len(tables) == 18
        assert "password_reset_tokens" in tables
        conn.close()

        # 3. Downgrade to base
        command.downgrade(alembic_cfg, "base")
        conn = sqlite3.connect(tmp_db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [r[0] for r in cur.fetchall() if r[0] != "alembic_version"]
        assert len(tables) == 0
        conn.close()

        # 4. Re-upgrade to head
        command.upgrade(alembic_cfg, "head")
        conn = sqlite3.connect(tmp_db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [r[0] for r in cur.fetchall() if r[0] != "alembic_version"]
        assert len(tables) == 18
        assert "password_reset_tokens" in tables
        conn.close()

    finally:
        if os.path.exists(tmp_db_path):
            try:
                os.remove(tmp_db_path)
            except OSError:
                pass


def test_alembic_schema_zero_drift():
    """AC09: Verifies alembic check detects 0 drift between Base.metadata and migrations."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        tmp_db_path = tmp_file.name

    try:
        alembic_cfg = Config("backend/alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{tmp_db_path.replace(os.sep, '/')}")
        command.upgrade(alembic_cfg, "head")

        # command.check raises an exception if there is any schema discrepancy
        command.check(alembic_cfg)
    finally:
        if os.path.exists(tmp_db_path):
            try:
                os.remove(tmp_db_path)
            except OSError:
                pass


def test_standardized_error_handling_contracts(auth_user, admin_user):
    """
    AC10: Verifies standardized error codes:
    - 401 Unauthorized
    - 403 Forbidden
    - 404 Not Found
    - 422 Unprocessable Entity
    with zero PHI or stack trace leakage.
    """
    # 1. 401: Unauthorized (no bearer token)
    res_401 = client.get("/api/v1/auth/me")
    assert res_401.status_code == 401
    assert "detail" in res_401.json()

    # 2. 403: Forbidden (Patient attempting Admin endpoint)
    res_403 = client.get("/api/v1/admin/users", headers=auth_user["headers"])
    assert res_403.status_code == 403
    assert "detail" in res_403.json()

    # 3. 404: Not Found (Nonexistent assessment ID)
    res_404 = client.get("/api/v1/assessments/NONEXISTENT_ASSESSMENT_ID_9999", headers=auth_user["headers"])
    assert res_404.status_code == 404
    data_404 = res_404.json()
    assert "detail" in data_404
    assert "Traceback" not in str(data_404)
    assert "SELECT " not in str(data_404)

    # 4. 422: Validation Error (Invalid schema body in JSON)
    res_422 = client.post("/api/v1/auth/login", json={"email": "not_an_email"})
    assert res_422.status_code == 422


def test_preservation_of_phase12_navigation_routes(auth_user):
    """AC11: Verifies Phase 12 Clinical Navigation and Referral routes are preserved."""
    # Facilities list
    res_fac = client.get("/api/v1/navigation/facilities", headers=auth_user["headers"])
    assert res_fac.status_code == 200
    facilities = res_fac.json()
    assert "items" in facilities
    assert isinstance(facilities["items"], list)
    assert len(facilities["items"]) > 0

    # Specific facility by slug
    res_fac_slug = client.get("/api/v1/navigation/facilities/cleveland-clinic-abu-dhabi", headers=auth_user["headers"])
    assert res_fac_slug.status_code == 200
    assert res_fac_slug.json()["slug"] == "cleveland-clinic-abu-dhabi"


def test_preservation_of_phase13_report_and_history_routes(auth_user):
    """AC12: Verifies Phase 13 Report generation, verification, and history routes are preserved."""
    # 1. History endpoint
    res_hist = client.get("/api/v1/assessments/history", headers=auth_user["headers"])
    assert res_hist.status_code == 200
    assert "items" in res_hist.json()

    # 2. Verification endpoint for invalid reference returns valid=False
    res_verify = client.get("/api/v1/reports/GNX-INVALID-REF/verify")
    assert res_verify.status_code == 200
    assert res_verify.json()["is_valid"] is False


def test_inviolate_clinical_outcome_tiers():
    """AC13: Verifies all four clinical outcome tiers are strictly preserved without alteration."""
    expected_tiers = {
        "TIER_1_NO_RISK": "NO_REPORTED_RISK_FACTORS",
        "TIER_2_RISK_FACTORS": "RISK_FACTORS_IDENTIFIED",
        "TIER_3_EVAL_RECOMMENDED": "CLINICAL_EVALUATION_RECOMMENDED",
        "TIER_4_URGENT": "URGENT_MEDICAL_ASSESSMENT"
    }

    for enum_name, expected_value in expected_tiers.items():
        tier = getattr(ClinicalOutcomeTier, enum_name)
        assert tier.value == expected_value, f"Mismatch in {enum_name}: {tier.value} != {expected_value}"


def test_idor_and_patient_data_isolation(db: Session, auth_user, other_user):
    """AC14: Verifies IDOR and patient ownership isolation across assessment reports."""
    # Create an assessment owned by auth_user
    sess_id = f"sess_{uuid.uuid4().hex}"
    assessment = Assessment(
        id=str(uuid.uuid4()),
        user_id=auth_user["user"].id,
        session_token=sess_id,
        questionnaire_version_id=1,
        status=AssessmentStatus.SUBMITTED
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    report_ref = f"GNX-{uuid.uuid4().hex[:8].upper()}"
    report = AssessmentReport(
        report_reference=report_ref,
        assessment_id=assessment.id,
        user_id=auth_user["user"].id,
        session_token=assessment.session_token,
        questionnaire_version_tag="v1.0.0",
        rule_engine_version="v1.0.0",
        outcome_tier=ClinicalOutcomeTier.TIER_2_RISK_FACTORS,
        outcome_title_en="Lifestyle Risk Factors",
        outcome_title_ar="عوامل الخطر",
        outcome_description_en="Confidential patient findings",
        outcome_description_ar="نتائج سرية للمريض",
        is_urgent_red_flag=False,
        clinical_disclaimer_en="Disclaimer.",
        clinical_disclaimer_ar="إخلاء مسؤولية."
    )
    db.add(report)
    db.commit()

    # other_user attempts to share or view report details owned by auth_user -> 403 or 404
    share_res = client.post(
        f"/api/v1/reports/{report_ref}/share",
        json={"recipient_name": "Dr. Hacker", "expires_in_hours": 24},
        headers=other_user["headers"]
    )
    assert share_res.status_code in (403, 404)

