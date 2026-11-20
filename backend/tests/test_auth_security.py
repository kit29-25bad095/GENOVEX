import os
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
import jwt

from app.core.config import Settings
from app.core.security import (
    User, RoleEnum, create_access_token, decode_access_token,
    get_current_user, require_roles, JWT_ALGORITHM
)

def test_sec_01_missing_token_unauthorized():
    """SEC-01: Missing token returns 401 Unauthorized."""
    mock_db = MagicMock()
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(auth=None, x_user_role=None, x_user_email=None, db=mock_db)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "not provided or invalid" in exc_info.value.detail

def test_sec_02_invalid_token_unauthorized():
    """SEC-02: Invalid/malformed token returns 401 Unauthorized."""
    mock_db = MagicMock()
    bad_auth = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid.token.payload")
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(auth=bad_auth, x_user_role=None, x_user_email=None, db=mock_db)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

def test_sec_03_expired_token_unauthorized():
    """SEC-03: Expired token returns 401 Unauthorized."""
    mock_db = MagicMock()
    # Create an already expired token (-10 minutes)
    expired_token = create_access_token({"sub": "patient@genovex.ae"}, expires_delta=timedelta(minutes=-10))
    auth = HTTPAuthorizationCredentials(scheme="Bearer", credentials=expired_token)
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(auth=auth, x_user_role=None, x_user_email=None, db=mock_db)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

def test_sec_04_valid_patient_token():
    """SEC-04: Valid patient token returns user identity successfully."""
    mock_db = MagicMock()
    mock_user = User(
        id=10,
        email="patient@genovex.ae",
        full_name="Patient User",
        role=RoleEnum.PATIENT,
        is_active=True
    )
    mock_db.query.return_value.filter.return_value.first.return_value = mock_user

    valid_token = create_access_token({"sub": "patient@genovex.ae"}, expires_delta=timedelta(minutes=60))
    auth = HTTPAuthorizationCredentials(scheme="Bearer", credentials=valid_token)

    user = get_current_user(auth=auth, x_user_role=None, x_user_email=None, db=mock_db)
    assert user is not None
    assert user.email == "patient@genovex.ae"
    assert user.role == RoleEnum.PATIENT

def test_sec_05_admin_endpoint_role_check():
    """SEC-05: Non-admin user accessing admin-required dependency raises 403 Forbidden."""
    patient_user = User(
        id=11,
        email="patient@genovex.ae",
        full_name="Patient User",
        role=RoleEnum.PATIENT,
        is_active=True
    )
    admin_checker = require_roles([RoleEnum.ADMIN])
    with pytest.raises(HTTPException) as exc_info:
        admin_checker(current_user=patient_user)
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "Access denied" in exc_info.value.detail

    # Verify admin user succeeds
    admin_user = User(
        id=1,
        email="admin@genovex.ae",
        full_name="Admin User",
        role=RoleEnum.ADMIN,
        is_active=True
    )
    checked_admin = admin_checker(current_user=admin_user)
    assert checked_admin.role == RoleEnum.ADMIN

def test_sec_06_simulated_auth_in_dev():
    """SEC-06: Simulated headers are honored in development when enabled."""
    from app.core import config
    orig_env = config.settings.ENVIRONMENT
    orig_debug = config.settings.DEBUG
    orig_allow = config.settings.ALLOW_SIMULATED_AUTH
    try:
        config.settings.ENVIRONMENT = "development"
        config.settings.DEBUG = True
        config.settings.ALLOW_SIMULATED_AUTH = True

        mock_db = MagicMock()
        mock_user = User(
            id=2,
            email="dev@genovex.ae",
            full_name="Dev User",
            role=RoleEnum.CLINICIAN,
            is_active=True
        )
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        user = get_current_user(auth=None, x_user_role=None, x_user_email="dev@genovex.ae", db=mock_db)
        assert user.email == "dev@genovex.ae"
        assert user.role == RoleEnum.CLINICIAN
    finally:
        config.settings.ENVIRONMENT = orig_env
        config.settings.DEBUG = orig_debug
        config.settings.ALLOW_SIMULATED_AUTH = orig_allow

def test_sec_07_simulated_auth_rejected_in_production():
    """SEC-07: Simulated auth headers are strictly rejected (401) in production."""
    from app.core import config
    orig_env = config.settings.ENVIRONMENT
    orig_debug = config.settings.DEBUG
    orig_allow = config.settings.ALLOW_SIMULATED_AUTH
    try:
        config.settings.ENVIRONMENT = "production"
        config.settings.DEBUG = False
        config.settings.ALLOW_SIMULATED_AUTH = True  # Attempt to bypass via flag

        mock_db = MagicMock()
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(
                auth=None,
                x_user_role="ADMIN",
                x_user_email="attacker@genovex.ae",
                db=mock_db
            )
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    finally:
        config.settings.ENVIRONMENT = orig_env
        config.settings.DEBUG = orig_debug
        config.settings.ALLOW_SIMULATED_AUTH = orig_allow

def test_sec_08_production_startup_validation():
    """
    SEC-08: Production startup checks fail-closed:
    - Default secret rejected in production independently of DEBUG.
    - DEBUG=True rejected in production.
    - VERCEL_ENV=production enforces the same checks.
    """
    # 1. Default secret rejected in production even if DEBUG=False
    with pytest.raises(ValueError, match="SECRET_KEY must be explicitly set"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            SECRET_KEY="genovex-secure-secret-key-uae-2026"
        )

    # 2. DEBUG=True rejected in production even with secure key
    with pytest.raises(ValueError, match="DEBUG must be False in production"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=True,
            SECRET_KEY="c4ca4238a0b923820dcc509a6f75849b"
        )

    # 3. VERCEL_ENV=production enforces checks even if ENVIRONMENT=development
    os.environ["VERCEL_ENV"] = "production"
    try:
        with pytest.raises(ValueError, match="SECRET_KEY must be explicitly set"):
            Settings(
                ENVIRONMENT="development",
                DEBUG=False,
                SECRET_KEY="genovex-secure-secret-key-uae-2026"
            )
        with pytest.raises(ValueError, match="DEBUG must be False in production"):
            Settings(
                ENVIRONMENT="development",
                DEBUG=True,
                SECRET_KEY="c4ca4238a0b923820dcc509a6f75849b"
            )
    finally:
        os.environ.pop("VERCEL_ENV", None)

    # 4. Valid production settings succeed
    valid_prod = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        SECRET_KEY="c4ca4238a0b923820dcc509a6f75849b"
    )
    assert valid_prod.ENVIRONMENT == "production"
    assert valid_prod.DEBUG is False
