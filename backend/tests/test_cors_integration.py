import os
import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.testclient import TestClient

from app.core import config
from app.core.config import (
    get_allowed_cors_origins,
    is_valid_production_origin,
    is_valid_dev_origin
)
from main import app as main_app

def create_cors_app(origins: list[str]) -> FastAPI:
    """Helper to instantiate a FastAPI app with specified CORS configuration."""
    test_app = FastAPI()
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    @test_app.get("/api/v1/test")
    def test_endpoint():
        return {"status": "ok"}
    return test_app

def test_production_validator_rules():
    """Verify production origin validator strictly enforces HTTPS and valid hostnames."""
    # Valid production origins
    assert is_valid_production_origin("https://genovex.vercel.app") is True
    assert is_valid_production_origin("https://sub.genovex.ae:8443") is True
    assert is_valid_production_origin("https://app-v2.genovex.com") is True

    # Invalid origins
    assert is_valid_production_origin("http://genovex.vercel.app") is False  # HTTP forbidden
    assert is_valid_production_origin("https://*") is False                  # Wildcard forbidden
    assert is_valid_production_origin("https://genovex.vercel.app/path") is False # Path forbidden
    assert is_valid_production_origin("https://user:pass@domain.com") is False # Auth info forbidden
    assert is_valid_production_origin("http://localhost:3000") is False      # Localhost forbidden in prod
    assert is_valid_production_origin("https://domain..com") is False        # Invalid hostname regex

def test_cors_precedence_production():
    """VERCEL_ENV=production or ENVIRONMENT=production must strictly allow production origins and exclude localhost."""
    orig_env = config.settings.ENVIRONMENT
    orig_vercel = os.environ.get("VERCEL_ENV")
    orig_cors = os.environ.get("CORS_ORIGINS")

    try:
        config.settings.ENVIRONMENT = "production"
        os.environ["VERCEL_ENV"] = "production"
        os.environ["CORS_ORIGINS"] = "https://custom.genovex.ae, http://localhost:3000, *"

        origins = get_allowed_cors_origins()
        assert "https://genovex.vercel.app" in origins
        assert "https://custom.genovex.ae" in origins
        assert "http://localhost:3000" not in origins
        assert "*" not in origins

        # Test preflight with credentials
        app = create_cors_app(origins)
        client = TestClient(app)

        # 1. Allowed canonical origin
        res = client.options(
            "/api/v1/test",
            headers={
                "Origin": "https://genovex.vercel.app",
                "Access-Control-Request-Method": "GET"
            }
        )
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") == "https://genovex.vercel.app"
        assert res.headers.get("access-control-allow-credentials") == "true"

        # 2. Localhost strictly rejected in production
        res_local = client.options(
            "/api/v1/test",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        assert res_local.headers.get("access-control-allow-origin") is None
    finally:
        config.settings.ENVIRONMENT = orig_env
        if orig_vercel is not None:
            os.environ["VERCEL_ENV"] = orig_vercel
        else:
            os.environ.pop("VERCEL_ENV", None)
        if orig_cors is not None:
            os.environ["CORS_ORIGINS"] = orig_cors
        else:
            os.environ.pop("CORS_ORIGINS", None)

def test_cors_precedence_contradictory_settings():
    """If ENVIRONMENT=development but VERCEL_ENV=production, production takes precedence."""
    orig_env = config.settings.ENVIRONMENT
    orig_vercel = os.environ.get("VERCEL_ENV")

    try:
        config.settings.ENVIRONMENT = "development"
        os.environ["VERCEL_ENV"] = "production"

        origins = get_allowed_cors_origins()
        assert "https://genovex.vercel.app" in origins
        assert "http://localhost:3000" not in origins
    finally:
        config.settings.ENVIRONMENT = orig_env
        if orig_vercel is not None:
            os.environ["VERCEL_ENV"] = orig_vercel
        else:
            os.environ.pop("VERCEL_ENV", None)

def test_cors_preview_precedence():
    """VERCEL_ENV=preview must allow exact VERCEL_URL and approved HTTPS custom origins, never localhost."""
    orig_env = config.settings.ENVIRONMENT
    orig_vercel = os.environ.get("VERCEL_ENV")
    orig_url = os.environ.get("VERCEL_URL")

    try:
        config.settings.ENVIRONMENT = "development"
        os.environ["VERCEL_ENV"] = "preview"
        os.environ["VERCEL_URL"] = "genovex-preview-deploy-123.vercel.app"

        origins = get_allowed_cors_origins()
        assert "https://genovex-preview-deploy-123.vercel.app" in origins
        assert "http://localhost:3000" not in origins

        app = create_cors_app(origins)
        client = TestClient(app)

        # Approved preview origin succeeds
        res = client.options(
            "/api/v1/test",
            headers={
                "Origin": "https://genovex-preview-deploy-123.vercel.app",
                "Access-Control-Request-Method": "POST"
            }
        )
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") == "https://genovex-preview-deploy-123.vercel.app"

        # Unapproved preview origin fails
        res_unapproved = client.options(
            "/api/v1/test",
            headers={
                "Origin": "https://evil-unapproved-preview.vercel.app",
                "Access-Control-Request-Method": "POST"
            }
        )
        assert res_unapproved.headers.get("access-control-allow-origin") is None
    finally:
        config.settings.ENVIRONMENT = orig_env
        if orig_vercel is not None:
            os.environ["VERCEL_ENV"] = orig_vercel
        else:
            os.environ.pop("VERCEL_ENV", None)
        if orig_url is not None:
            os.environ["VERCEL_URL"] = orig_url
        else:
            os.environ.pop("VERCEL_URL", None)

def test_cors_staging_precedence():
    """ENVIRONMENT=staging allows only approved custom HTTPS origins, never localhost."""
    orig_env = config.settings.ENVIRONMENT
    orig_cors = os.environ.get("CORS_ORIGINS")

    try:
        config.settings.ENVIRONMENT = "staging"
        os.environ["CORS_ORIGINS"] = "https://staging.genovex.ae, http://localhost:3000"

        origins = get_allowed_cors_origins()
        assert "https://staging.genovex.ae" in origins
        assert "http://localhost:3000" not in origins
    finally:
        config.settings.ENVIRONMENT = orig_env
        if orig_cors is not None:
            os.environ["CORS_ORIGINS"] = orig_cors
        else:
            os.environ.pop("CORS_ORIGINS", None)

def test_cors_fail_closed_unknown_environment():
    """Unknown or invalid environment combinations fail-closed to approved HTTPS origins only."""
    orig_env = config.settings.ENVIRONMENT
    orig_cors = os.environ.get("CORS_ORIGINS")

    try:
        config.settings.ENVIRONMENT = "custom_unknown_env"
        os.environ["CORS_ORIGINS"] = "https://safe-domain.ae, http://localhost:3000"

        origins = get_allowed_cors_origins()
        assert "https://safe-domain.ae" in origins
        assert "http://localhost:3000" not in origins
    finally:
        config.settings.ENVIRONMENT = orig_env
        if orig_cors is not None:
            os.environ["CORS_ORIGINS"] = orig_cors
        else:
            os.environ.pop("CORS_ORIGINS", None)

def test_cors_main_app_integration():
    """Verify live main_app preflight headers."""
    client = TestClient(main_app)
    # Origin from unauthorized domain
    res = client.options(
        "/api/v1/health",
        headers={
            "Origin": "https://unauthorized-attacker.com",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert res.headers.get("access-control-allow-origin") is None
