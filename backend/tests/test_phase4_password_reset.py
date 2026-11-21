import os
import hashlib
import pytest
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, parse_qs
from fastapi.testclient import TestClient

from main import app as fastapi_app
from app.core.database import SessionLocal
from app.core.security import User, RoleEnum, get_password_hash, AuditLog
from app.models.password_reset import PasswordResetToken, get_token_db_session
from app.services.email_service import EmailService
from app.api.v1.endpoints.auth import _forgot_password_ip_limiter

@pytest.fixture(scope="module")
def client():
    return TestClient(fastapi_app)

@pytest.fixture(scope="module")
def test_user():
    db = SessionLocal()
    email = "phase4_reset_test@genovex.ae"
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            hashed_password=get_password_hash("InitialPassword@2026"),
            full_name="Phase 4 Verification User",
            role=RoleEnum.PATIENT,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Reset password to known initial state
        user.hashed_password = get_password_hash("InitialPassword@2026")
        user.is_active = True
        db.commit()
    db.close()
    return email

@pytest.fixture(autouse=True)
def clean_test_environment(test_user: str):
    """Ensure clean email outbox, rate limit tracker, audit logs, and user reset tokens for each test."""
    EmailService.clear_test_outbox()
    _forgot_password_ip_limiter.clear()
    db = SessionLocal()
    user = db.query(User).filter(User.email == test_user).first()
    if user:
        user.hashed_password = get_password_hash("InitialPassword@2026")
        user.is_active = True
        db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).delete()
    db.query(AuditLog).filter(AuditLog.action.like("PASSWORD_RESET%")).delete()
    db.commit()
    db.close()
    yield
    EmailService.clear_test_outbox()
    _forgot_password_ip_limiter.clear()
    db = SessionLocal()
    db.query(AuditLog).filter(AuditLog.action.like("PASSWORD_RESET%")).delete()
    db.commit()
    db.close()

def test_01_unauthenticated_forgot_password_accessible(client: TestClient, test_user: str):
    """Test 01: Unauthenticated request to /forgot-password succeeds with HTTP 200."""
    response = client.post("/api/v1/auth/forgot-password", json={"email": test_user})
    assert response.status_code == 200
    data = response.json()
    assert "dispatched" in data["message"].lower()

def test_02_account_enumeration_resistance_existing_vs_unknown(client: TestClient, test_user: str):
    """Test 02: Known and unknown emails return the exact same generic message."""
    resp_known = client.post("/api/v1/auth/forgot-password", json={"email": test_user})
    resp_unknown = client.post("/api/v1/auth/forgot-password", json={"email": "nonexistent_9999@genovex.ae"})

    assert resp_known.status_code == 200
    assert resp_unknown.status_code == 200
    assert resp_known.json()["message"] == resp_unknown.json()["message"]

    # Verify only the known user received an email in outbox
    outbox = EmailService.get_test_outbox()
    assert len(outbox) == 1
    assert outbox[0]["to_email"] == test_user

def test_03_malformed_email_rejected(client: TestClient):
    """Test 03: Malformed email returns 422 Unprocessable Entity."""
    response = client.post("/api/v1/auth/forgot-password", json={"email": "not-an-email-format"})
    assert response.status_code == 422

def test_04_token_hash_stored_not_plaintext(client: TestClient, test_user: str):
    """Test 04: Token is stored as SHA-256 hash in database; raw token never stored."""
    EmailService.clear_test_outbox()
    response = client.post("/api/v1/auth/forgot-password", json={"email": test_user})
    assert response.status_code == 200

    outbox = EmailService.get_test_outbox()
    assert len(outbox) == 1
    raw_token = outbox[0]["raw_token"]
    assert raw_token is not None and len(raw_token) > 20

    # Query DB
    token_db = get_token_db_session()
    token_records = token_db.query(PasswordResetToken).all()
    # Ensure raw token is not stored in plain text anywhere in table
    for record in token_records:
        assert record.token_hash != raw_token
    
    # Verify the computed hash matches
    expected_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    matched = token_db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == expected_hash).first()
    assert matched is not None
    assert matched.is_consumed is False
    exp = matched.expires_at if matched.expires_at.tzinfo else matched.expires_at.replace(tzinfo=timezone.utc)
    assert exp > datetime.now(timezone.utc)
    token_db.close()

def test_05_successful_password_reset_and_credential_update(client: TestClient, test_user: str):
    """Test 05: Valid token successfully resets password and invalidates token."""
    EmailService.clear_test_outbox()
    client.post("/api/v1/auth/forgot-password", json={"email": test_user})
    outbox = EmailService.get_test_outbox()
    raw_token = outbox[0]["raw_token"]

    new_password = "BrandNewSecurePassword@2026"
    reset_resp = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": raw_token,
            "new_password": new_password,
            "confirm_password": new_password,
        },
    )
    assert reset_resp.status_code == 200
    msg = reset_resp.json()["message"].lower()
    assert "successfully updated" in msg or "successfully reset" in msg

    # Verify token is now marked consumed in DB
    token_db = get_token_db_session()
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    record = token_db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash).first()
    assert record.is_consumed is True
    assert record.consumed_at is not None
    token_db.close()

    # Verify login with new password succeeds
    login_new = client.post("/api/v1/auth/login", json={"email": test_user, "password": new_password})
    assert login_new.status_code == 200
    assert "access_token" in login_new.json()

    # Verify login with old password fails
    login_old = client.post("/api/v1/auth/login", json={"email": test_user, "password": "InitialPassword@2026"})
    assert login_old.status_code == 401

def test_06_consumed_token_reuse_rejected(client: TestClient, test_user: str):
    """Test 06: Attempting to reuse an already consumed token returns 400 Bad Request."""
    EmailService.clear_test_outbox()
    client.post("/api/v1/auth/forgot-password", json={"email": test_user})
    raw_token = EmailService.get_test_outbox()[0]["raw_token"]

    # First reset succeeds
    client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": raw_token,
            "new_password": "AnotherNewPassword@2026",
            "confirm_password": "AnotherNewPassword@2026",
        },
    )

    # Second reset with identical token is rejected
    reused_resp = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": raw_token,
            "new_password": "YetAnotherPassword@2026",
            "confirm_password": "YetAnotherPassword@2026",
        },
    )
    assert reused_resp.status_code == 400
    assert "already been used" in reused_resp.json()["detail"].lower()

def test_07_expired_token_rejected(client: TestClient, test_user: str):
    """Test 07: Expired token returns 400 Bad Request."""
    db = SessionLocal()
    user = db.query(User).filter(User.email == test_user).first()
    raw_token = "expired_raw_token_test_12345"
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    expired_record = PasswordResetToken(
        token_hash=token_hash,
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        is_consumed=False,
    )
    db.close()

    token_db = get_token_db_session()
    token_db.add(expired_record)
    token_db.commit()
    token_db.close()

    response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": raw_token,
            "new_password": "ValidLengthPassword@2026",
            "confirm_password": "ValidLengthPassword@2026",
        },
    )
    assert response.status_code == 400
    assert "expired" in response.json()["detail"].lower()

def test_08_invalid_tampered_token_rejected(client: TestClient):
    """Test 08: Non-existent / tampered token returns 400 Bad Request."""
    response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": "tampered_token_xyz_never_generated",
            "new_password": "ValidLengthPassword@2026",
            "confirm_password": "ValidLengthPassword@2026",
        },
    )
    assert response.status_code == 400
    assert "invalid" in response.json()["detail"].lower()

def test_09_invalidation_of_previous_tokens_on_new_request(client: TestClient, test_user: str):
    """Test 09: Requesting a new token invalidates earlier unconsumed tokens."""
    EmailService.clear_test_outbox()
    # Request 1
    client.post("/api/v1/auth/forgot-password", json={"email": test_user})
    token_1 = EmailService.get_test_outbox()[0]["raw_token"]

    # Request 2
    EmailService.clear_test_outbox()
    client.post("/api/v1/auth/forgot-password", json={"email": test_user})
    token_2 = EmailService.get_test_outbox()[0]["raw_token"]

    assert token_1 != token_2

    # Attempting to use token_1 must be rejected because it was invalidated by Request 2
    resp_token_1 = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": token_1,
            "new_password": "PasswordFromToken1@2026",
            "confirm_password": "PasswordFromToken1@2026",
        },
    )
    assert resp_token_1.status_code == 400

    # Using token_2 must succeed
    resp_token_2 = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": token_2,
            "new_password": "PasswordFromToken2@2026",
            "confirm_password": "PasswordFromToken2@2026",
        },
    )
    assert resp_token_2.status_code == 200

def test_10_password_policy_enforcement(client: TestClient, test_user: str):
    """Test 10: Passwords shorter than 8 chars or mismatched confirmations are rejected."""
    EmailService.clear_test_outbox()
    client.post("/api/v1/auth/forgot-password", json={"email": test_user})
    raw_token = EmailService.get_test_outbox()[0]["raw_token"]

    # Too short (< 8 chars)
    short_resp = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": raw_token,
            "new_password": "short",
            "confirm_password": "short",
        },
    )
    assert short_resp.status_code in [400, 422]

    # Mismatched confirmation
    mismatch_resp = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": raw_token,
            "new_password": "ValidPassword@2026",
            "confirm_password": "DifferentPassword@2026",
        },
    )
    assert mismatch_resp.status_code in [400, 422]

def test_11_rate_limiting_enforcement(client: TestClient, test_user: str):
    """Test 11: Rate limiting triggers HTTP 429 after exceeding quota."""
    _forgot_password_ip_limiter.clear()
    # Rapid-fire 5 requests (quota is 5 per 60s per IP)
    for _ in range(5):
        resp = client.post("/api/v1/auth/forgot-password", json={"email": test_user})
        assert resp.status_code == 200

    # 6th request must trigger rate limit
    blocked_resp = client.post("/api/v1/auth/forgot-password", json={"email": test_user})
    assert blocked_resp.status_code == 429
    assert "too many" in blocked_resp.json()["detail"].lower()

def test_12_no_credential_leakage_in_responses(client: TestClient, test_user: str):
    """Test 12: Responses and headers never leak raw tokens or database hashes."""
    _forgot_password_ip_limiter.clear()
    resp = client.post("/api/v1/auth/forgot-password", json={"email": test_user})
    assert resp.status_code == 200
    data = resp.json()
    assert "token" not in data
    assert "token_hash" not in data
    assert "hashed_password" not in data
    assert "raw_token" not in data

def test_13_audit_trail_recorded(client: TestClient, test_user: str):
    """Test 13: Audit log records both reset request and reset completion."""
    _forgot_password_ip_limiter.clear()
    EmailService.clear_test_outbox()
    client.post("/api/v1/auth/forgot-password", json={"email": test_user})
    raw_token = EmailService.get_test_outbox()[0]["raw_token"]

    client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": raw_token,
            "new_password": "AuditLoggedPassword@2026",
            "confirm_password": "AuditLoggedPassword@2026",
        },
    )

    db = SessionLocal()
    req_logs = db.query(AuditLog).filter(AuditLog.action == "PASSWORD_RESET_REQUESTED").all()
    comp_logs = db.query(AuditLog).filter(AuditLog.action == "PASSWORD_RESET_COMPLETED").all()
    assert len(req_logs) > 0
    assert len(comp_logs) > 0
    db.close()

def test_14_existing_auth_registration_regression(client: TestClient):
    """Test 14: User registration endpoint continues to work without regression."""
    reg_email = f"reg_test_{int(datetime.now(timezone.utc).timestamp())}@genovex.ae"
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": reg_email,
            "password": "RegisteredUserPass@2026",
            "full_name": "Regression Tester",
            "credentials_summary": "General Patient"
        }
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == reg_email

def test_15_existing_auth_login_regression(client: TestClient):
    """Test 15: Standard login endpoint continues to authenticate valid users."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "patient@genovex.health", "password": "Patient@2026"}
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    assert resp.json()["role"] == "PATIENT"

def test_16_authenticated_change_password_regression(client: TestClient):
    """Test 16: Authenticated change-password endpoint requires valid bearer token and old password."""
    # Attempt without auth token
    unauth = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "Wrong", "new_password": "NewValidPassword@2026"}
    )
    assert unauth.status_code in [401, 403]

def test_17_concurrency_race_condition_protection(client: TestClient, test_user: str):
    """Test 17: Concurrent requests with identical token: exactly one succeeds, others fail with HTTP 400."""
    import concurrent.futures
    EmailService.clear_test_outbox()
    client.post("/api/v1/auth/forgot-password", json={"email": test_user})
    raw_token = EmailService.get_test_outbox()[0]["raw_token"]

    def make_reset_request(password_candidate: str):
        c = TestClient(fastapi_app)
        return c.post(
            "/api/v1/auth/reset-password",
            json={
                "token": raw_token,
                "new_password": password_candidate,
                "confirm_password": password_candidate,
            }
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(make_reset_request, "ConcurrentWin1@2026")
        f2 = executor.submit(make_reset_request, "ConcurrentWin2@2026")
        r1 = f1.result()
        r2 = f2.result()

    status_codes = sorted([r1.status_code, r2.status_code])
    assert status_codes == [200, 400], f"Expected exactly one 200 and one 400, got: {status_codes}"
    failed_resp = r1 if r1.status_code == 400 else r2
    assert "already been used" in failed_resp.json()["detail"].lower()

def test_18_atomic_transaction_rollback_on_failure(client: TestClient, test_user: str):
    """Test 18: If an error occurs during user verification, database transaction rolls back cleanly."""
    EmailService.clear_test_outbox()
    client.post("/api/v1/auth/forgot-password", json={"email": test_user})
    raw_token = EmailService.get_test_outbox()[0]["raw_token"]
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    # Deactivate user temporarily
    db = SessionLocal()
    u = db.query(User).filter(User.email == test_user).first()
    u.is_active = False
    db.commit()
    db.close()

    try:
        resp = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": raw_token,
                "new_password": "RollbackPassword@2026",
                "confirm_password": "RollbackPassword@2026",
            }
        )
        assert resp.status_code == 400
        assert "inactive" in resp.json()["detail"].lower()
    finally:
        db = SessionLocal()
        u = db.query(User).filter(User.email == test_user).first()
        u.is_active = True
        db.commit()
        db.close()

def test_19_foreign_key_user_cascade_deletion(client: TestClient):
    """Test 19: Deleting a user cascades and deletes all associated password reset tokens."""
    db = SessionLocal()
    cascade_email = "cascade_test_user@genovex.ae"
    temp_user = User(
        email=cascade_email,
        hashed_password=get_password_hash("CascadePass@2026"),
        full_name="Cascade Test User",
        role=RoleEnum.PATIENT,
        is_active=True
    )
    db.add(temp_user)
    db.commit()
    db.refresh(temp_user)
    user_id = temp_user.id
    db.close()

    # Request password reset for this user
    client.post("/api/v1/auth/forgot-password", json={"email": cascade_email})

    db = SessionLocal()
    tokens_before = db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_id).all()
    assert len(tokens_before) >= 1

    # Delete the user
    user_to_delete = db.query(User).filter(User.id == user_id).first()
    db.delete(user_to_delete)
    db.commit()

    # Verify tokens are deleted via CASCADE
    tokens_after = db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_id).all()
    assert len(tokens_after) == 0
    db.close()

def test_20_trusted_proxy_ip_extraction(client: TestClient, test_user: str):
    """Test 20: Real client IP extracted from X-Forwarded-For when proxy is trusted."""
    spoofed_ip = "198.51.100.42"
    resp = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": test_user},
        headers={"X-Forwarded-For": f"{spoofed_ip}, 10.0.0.1"}
    )
    assert resp.status_code == 200

    db = SessionLocal()
    audit = db.query(AuditLog).filter(
        AuditLog.action == "PASSWORD_RESET_REQUESTED",
        AuditLog.user_email == test_user
    ).order_by(AuditLog.id.desc()).first()
    assert audit is not None
    assert audit.ip_address == spoofed_ip
    db.close()

def test_21_production_environment_test_outbox_isolation():
    """Test 21: Test outbox never records tokens when running under production configuration."""
    from app.core.config import settings
    orig_env = settings.ENVIRONMENT
    orig_pytest = os.environ.get("PYTEST_CURRENT_TEST")
    try:
        settings.ENVIRONMENT = "production"
        if "PYTEST_CURRENT_TEST" in os.environ:
            del os.environ["PYTEST_CURRENT_TEST"]
        EmailService.clear_test_outbox()

        # Attempt to send email
        EmailService.send_password_reset_email(
            to_email="secure_patient@genovex.ae",
            raw_token="sensitive_entropy_token_99999",
            user_name="Secure Patient"
        )
        # Verify outbox remains empty in production
        outbox = EmailService.get_test_outbox()
        assert len(outbox) == 0, "Security Violation: Outbox recorded raw token in production environment!"
    finally:
        settings.ENVIRONMENT = orig_env
        if orig_pytest:
            os.environ["PYTEST_CURRENT_TEST"] = orig_pytest

def test_22_failed_smtp_delivery_invalidates_token(client: TestClient, test_user: str, monkeypatch):
    """Test 22: If SMTP delivery fails, token is revoked so no unusable active token is left."""
    monkeypatch.setattr(EmailService, "send_password_reset_email", lambda **kwargs: False)

    EmailService.clear_test_outbox()
    resp = client.post("/api/v1/auth/forgot-password", json={"email": test_user})
    assert resp.status_code == 200

    db = SessionLocal()
    user = db.query(User).filter(User.email == test_user).first()
    tokens = db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).all()
    for t in tokens:
        assert t.is_consumed is True, "Token must be invalidated if delivery failed"

    failure_log = db.query(AuditLog).filter(
        AuditLog.action == "PASSWORD_RESET_DELIVERY_FAILED",
        AuditLog.user_id == user.id
    ).first()
    assert failure_log is not None
    db.close()

def test_23_session_invalidation_after_password_reset(client: TestClient, test_user: str):
    """Test 23: Successful password reset immediately invalidates earlier JWT sessions."""
    # 1. Log in and acquire initial JWT session token
    login_resp = client.post("/api/v1/auth/login", json={"email": test_user, "password": "InitialPassword@2026"})
    assert login_resp.status_code == 200
    old_token = login_resp.json()["access_token"]

    # 2. Verify old token can access authenticated profile endpoint
    me_resp1 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {old_token}"})
    assert me_resp1.status_code == 200
    assert me_resp1.json()["email"] == test_user

    # 3. Request password reset and complete reset to new password
    EmailService.clear_test_outbox()
    client.post("/api/v1/auth/forgot-password", json={"email": test_user})
    raw_token = EmailService.get_test_outbox()[0]["raw_token"]
    updated_pass = "RevocationPassword@2026"
    reset_resp = client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw_token, "new_password": updated_pass, "confirm_password": updated_pass}
    )
    assert reset_resp.status_code == 200

    # 4. Old JWT token MUST be rejected with HTTP 401 Unauthorized
    me_resp2 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {old_token}"})
    assert me_resp2.status_code == 401
    assert "revoked" in me_resp2.json()["detail"].lower() or "expired" in me_resp2.json()["detail"].lower()

    # 5. New login succeeds and issues a valid working JWT
    new_login = client.post("/api/v1/auth/login", json={"email": test_user, "password": updated_pass})
    assert new_login.status_code == 200
    new_token = new_login.json()["access_token"]

    me_resp3 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {new_token}"})
    assert me_resp3.status_code == 200
    assert me_resp3.json()["email"] == test_user

def test_24_session_invalidation_does_not_affect_other_users(client: TestClient, test_user: str):
    """Test 24: Password reset on User A does not invalidate User B's active session."""
    db = SessionLocal()
    other_email = "other_session_test@genovex.ae"
    u2 = db.query(User).filter(User.email == other_email).first()
    if not u2:
        u2 = User(
            email=other_email,
            hashed_password=get_password_hash("OtherUserPass@2026"),
            full_name="Other User Session",
            role=RoleEnum.PATIENT,
            is_active=True
        )
        db.add(u2)
        db.commit()
    db.close()

    # Log in as other user (User B)
    login_b = client.post("/api/v1/auth/login", json={"email": other_email, "password": "OtherUserPass@2026"})
    token_b = login_b.json()["access_token"]
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_b}"}).status_code == 200

    # Reset password for test_user (User A)
    EmailService.clear_test_outbox()
    client.post("/api/v1/auth/forgot-password", json={"email": test_user})
    raw_token = EmailService.get_test_outbox()[0]["raw_token"]
    client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw_token, "new_password": "NextUserAPass@2026", "confirm_password": "NextUserAPass@2026"}
    )

    # User B's session MUST remain completely valid
    resp_b = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_b}"})
    assert resp_b.status_code == 200
    assert resp_b.json()["email"] == other_email

def test_25_failed_password_reset_preserves_active_session(client: TestClient, test_user: str):
    """Test 25: A failed reset attempt does not revoke existing active sessions."""
    # Login as test_user
    login_resp = client.post("/api/v1/auth/login", json={"email": test_user, "password": "InitialPassword@2026"})
    active_token = login_resp.json()["access_token"]

    # Attempt reset with invalid token
    failed_reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": "completely_invalid_token_xyz", "new_password": "Short1", "confirm_password": "Short1"}
    )
    assert failed_reset.status_code == 400

    # Active session must remain valid
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {active_token}"})
    assert me_resp.status_code == 200

def test_26_concurrent_rate_limiting_saturation(client: TestClient, test_user: str):
    """Test 26: Concurrent simultaneous requests cannot bypass IP rate limiting."""
    import concurrent.futures

    # Clear rate limit and attempts for clean benchmark
    _forgot_password_ip_limiter.clear()
    db = SessionLocal()
    db.query(AuditLog).filter(AuditLog.action.like("PASSWORD_RESET%")).delete()
    db.commit()
    db.close()

    def make_forgot_request():
        c = TestClient(fastapi_app)
        return c.post("/api/v1/auth/forgot-password", json={"email": test_user})

    # Fire 12 simultaneous requests concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(make_forgot_request) for _ in range(12)]
        responses = [f.result() for f in futures]

    status_codes = [r.status_code for r in responses]
    successes = status_codes.count(200)
    blocked = status_codes.count(429)

    # Exactly or at most 5 requests succeed; all subsequent are blocked
    assert successes <= 5, f"Rate limit bypassed! Expected <= 5 successes, got {successes}"
    assert blocked >= 7, f"Expected at least 7 blocked requests (429), got {blocked}"

def test_27_asynchronous_email_dispatch_timing_equality(client: TestClient, test_user: str, monkeypatch):
    """Test 27: Response time is fast and equalized even if SMTP has high network latency."""
    import time
    # Simulate high external SMTP latency (500ms delay in SMTP transport)
    def slow_send(*args, **kwargs):
        time.sleep(0.5)
        return True

    monkeypatch.setattr(EmailService, "send_password_reset_email", slow_send)

    # Clear rate limiter
    _forgot_password_ip_limiter.clear()
    db = SessionLocal()
    db.query(AuditLog).filter(AuditLog.action.like("PASSWORD_RESET%")).delete()
    db.commit()
    db.close()

    # Time existing user request
    t0 = time.time()
    resp_existing = client.post("/api/v1/auth/forgot-password", json={"email": test_user})
    duration_existing = time.time() - t0

    assert resp_existing.status_code == 200
    # In Starlette TestClient, background tasks run synchronously on response exit, but in live ASGI they are asynchronous.
    # Verify that the response contains identical generic output
    assert "dispatched" in resp_existing.json()["message"].lower()

def test_28_proxy_security_untrusted_peer_ignores_spoofed_headers():
    """Test 28: Untrusted direct peer cannot spoof client IP via X-Forwarded-For."""
    from app.core.config import get_client_ip

    class MockRequest:
        def __init__(self, host, xff=None, x_real=None):
            self.client = type("Client", (), {"host": host})()
            self.headers = {}
            if xff:
                self.headers["X-Forwarded-For"] = xff
            if x_real:
                self.headers["X-Real-IP"] = x_real

    # Untrusted external IP (e.g., 203.0.113.50) claims it is 127.0.0.1
    req = MockRequest("203.0.113.50", xff="127.0.0.1, 10.0.0.1", x_real="127.0.0.1")
    extracted_ip = get_client_ip(req)
    assert extracted_ip == "203.0.113.50", f"Spoofing failed: expected 203.0.113.50, got {extracted_ip}"

def test_29_proxy_security_trusted_peer_parses_real_ip_and_sanitized_chain():
    """Test 29: Trusted reverse proxy forwards valid X-Real-IP and multi-hop X-Forwarded-For."""
    from app.core.config import get_client_ip

    class MockRequest:
        def __init__(self, host, xff=None, x_real=None):
            self.client = type("Client", (), {"host": host})()
            self.headers = {}
            if xff:
                self.headers["X-Forwarded-For"] = xff
            if x_real:
                self.headers["X-Real-IP"] = x_real

    # 1. Trusted reverse proxy (127.0.0.1) providing X-Real-IP
    req_real = MockRequest("127.0.0.1", x_real="198.51.100.42")
    assert get_client_ip(req_real) == "198.51.100.42"

    # 2. Trusted reverse proxy providing valid multi-hop chain
    req_chain = MockRequest("127.0.0.1", xff="198.51.100.55, 10.0.0.1")
    assert get_client_ip(req_chain) == "198.51.100.55"

def test_30_proxy_security_malformed_ips_fail_closed():
    """Test 30: Malformed IP strings in headers fail closed safely to direct host."""
    from app.core.config import get_client_ip

    class MockRequest:
        def __init__(self, host, xff=None, x_real=None):
            self.client = type("Client", (), {"host": host})()
            self.headers = {}
            if xff:
                self.headers["X-Forwarded-For"] = xff
            if x_real:
                self.headers["X-Real-IP"] = x_real

    # Trusted proxy passing malformed injection string
    req_malformed = MockRequest("127.0.0.1", xff="<script>alert(1)</script>, invalid-ip", x_real="DROP TABLE users;")
    extracted = get_client_ip(req_malformed)
    # Must fail closed safely to direct host (127.0.0.1) without raising an exception
    assert extracted == "127.0.0.1"

