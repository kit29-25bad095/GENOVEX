import os
import re
from pathlib import Path
from urllib.parse import urlparse
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Authoritative repository root & database path resolution
PROJECT_ROOT = Path(__file__).resolve().parents[3]
AUTHORITATIVE_DB_PATH = PROJECT_ROOT / "genovex.db"

# RFC 1123 Hostname Validation Regex
HOSTNAME_REGEX = re.compile(
    r"^(?=.{1,253}$)(?:(?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+(?:[a-zA-Z]{2,63}|xn--[a-zA-Z0-9]+)$"
)

def is_valid_production_origin(origin: str) -> bool:
    """Production validator: strict HTTPS, valid RFC 1123 host, no credentials, no path, valid port."""
    if not origin or "*" in origin:
        return False
    try:
        parsed = urlparse(origin)
    except Exception:
        return False
    if parsed.scheme != "https":
        return False
    if parsed.username or parsed.password:
        return False
    try:
        port = parsed.port
        if port is not None and not (1 <= port <= 65535):
            return False
    except ValueError:
        return False
    try:
        host = parsed.hostname
    except ValueError:
        return False
    if not host or not HOSTNAME_REGEX.match(host):
        return False
    if parsed.path not in ("", "/"):
        return False
    if parsed.params or parsed.query or parsed.fragment:
        return False
    return True

def is_valid_dev_origin(origin: str) -> bool:
    """Development validator: permits http/https, localhost/loopback or valid host, no credentials, valid port."""
    if not origin or "*" in origin:
        return False
    try:
        parsed = urlparse(origin)
    except Exception:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    if parsed.username or parsed.password:
        return False
    try:
        port = parsed.port
        if port is not None and not (1 <= port <= 65535):
            return False
    except ValueError:
        return False
    try:
        host = parsed.hostname
    except ValueError:
        return False
    if not host:
        return False
    if host != "localhost" and host not in ("127.0.0.1", "::1") and not HOSTNAME_REGEX.match(host):
        return False
    if parsed.path not in ("", "/"):
        return False
    if parsed.params or parsed.query or parsed.fragment:
        return False
    return True

class Settings(BaseSettings):
    PROJECT_NAME: str = "GENOVEX Healthcare Platform"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{AUTHORITATIVE_DB_PATH.as_posix()}")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "genovex-secure-secret-key-uae-2026")
    ALLOW_SIMULATED_AUTH: bool = os.getenv("ALLOW_SIMULATED_AUTH", "True").lower() == "true" # Dev sandbox only, disabled in production

    # Database Connection Pooling Settings (Phase 14: PostgreSQL Readiness)
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "20"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "1800"))
    DB_POOL_PRE_PING: bool = os.getenv("DB_POOL_PRE_PING", "True").lower() == "true"
    
    # Target Market & Language
    DEFAULT_LANGUAGE: str = "en"
    SUPPORTED_LANGUAGES: list[str] = ["en", "ar"]

    # AI Integration Settings (Phase 9)
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "mock")
    AI_MODEL: str = os.getenv("AI_MODEL", "gemini-1.5-flash")
    AI_API_KEY: Optional[str] = os.getenv("AI_API_KEY", None)
    AI_REQUEST_TIMEOUT_SECONDS: int = int(os.getenv("AI_REQUEST_TIMEOUT_SECONDS", "15"))
    AI_MAX_RETRIES: int = int(os.getenv("AI_MAX_RETRIES", "2"))
    AI_RATE_LIMIT_PER_MINUTE: int = int(os.getenv("AI_RATE_LIMIT_PER_MINUTE", "60"))
    AI_MAX_INPUT_CHARS: int = int(os.getenv("AI_MAX_INPUT_CHARS", "2000"))
    
    # Phase 18 Maintenance & Reliability Configurations
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENABLE_STRUCTURED_LOGGING: bool = os.getenv("ENABLE_STRUCTURED_LOGGING", "True").lower() == "true"
    BACKUP_DIR: str = os.getenv("BACKUP_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "backups"))
    BACKUP_RETENTION_COUNT: int = int(os.getenv("BACKUP_RETENTION_COUNT", "7"))
    
    # AI Monitoring & Circuit Breaker Limits
    AI_CIRCUIT_BREAKER_MAX_FAILURES: int = int(os.getenv("AI_CIRCUIT_BREAKER_MAX_FAILURES", "3"))
    AI_CIRCUIT_BREAKER_COOLDOWN_SEC: int = int(os.getenv("AI_CIRCUIT_BREAKER_COOLDOWN_SEC", "60"))
    AI_REQUEST_TIMEOUT_SEC: float = float(os.getenv("AI_REQUEST_TIMEOUT_SEC", "10.0"))
    
    # Maintenance Scheduler
    ENABLE_BACKGROUND_SCHEDULER: bool = os.getenv("ENABLE_BACKGROUND_SCHEDULER", "True").lower() == "true"
    MAINTENANCE_INTERVAL_MINUTES: int = int(os.getenv("MAINTENANCE_INTERVAL_MINUTES", "60"))

    model_config = SettingsConfigDict(case_sensitive=True)

    def __init__(self, **values):
        super().__init__(**values)
        is_production = (
            self.ENVIRONMENT.lower() == "production" 
            or os.getenv("VERCEL_ENV", "").lower() == "production"
        )
        if is_production:
            # 1. Independent secret rejection: Cannot be bypassed by DEBUG
            if self.SECRET_KEY == "genovex-secure-secret-key-uae-2026":
                raise ValueError("CRITICAL SECURITY ERROR: SECRET_KEY must be explicitly set to a cryptographically secure random value in production!")
            # 2. Strict debug rejection: Debug mode is prohibited in production
            if self.DEBUG:
                raise ValueError("CRITICAL SECURITY ERROR: DEBUG must be False in production!")

settings = Settings()

def get_allowed_cors_origins() -> List[str]:
    env = (settings.ENVIRONMENT or "").strip().lower()
    vercel_env = (os.getenv("VERCEL_ENV") or "").strip().lower()
    raw_custom = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]

    # 1. PREVIEW PRECEDENCE:
    # If running under Vercel preview, preview rules apply unconditionally.
    if vercel_env == "preview":
        origins = []
        vercel_url = os.getenv("VERCEL_URL")
        if vercel_url:
            candidate = f"https://{vercel_url.strip()}"
            if is_valid_production_origin(candidate):
                origins.append(candidate.rstrip("/"))
        for item in raw_custom:
            if is_valid_production_origin(item):
                origins.append(item.rstrip("/"))
        return sorted(list(set(origins)))

    # 2. PRODUCTION PRECEDENCE:
    # If either VERCEL_ENV or ENVIRONMENT indicates production, production rules apply unconditionally.
    # Localhost is strictly prohibited.
    if vercel_env == "production" or env == "production":
        origins = ["https://genovex.vercel.app"]
        for item in raw_custom:
            if is_valid_production_origin(item):
                origins.append(item.rstrip("/"))
        return sorted(list(set(origins)))

    # 3. STAGING:
    # Localhost is strictly prohibited. Only explicitly approved HTTPS custom origins.
    if env == "staging":
        return sorted(list(set([o.rstrip("/") for o in raw_custom if is_valid_production_origin(o)])))

    # 4. EXPLICIT DEVELOPMENT:
    # Only if ENVIRONMENT == "development" AND VERCEL_ENV in ("", "development").
    if env == "development" and vercel_env in ("", "development"):
        dev_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
        for item in raw_custom:
            if is_valid_dev_origin(item):
                dev_origins.append(item.rstrip("/"))
        return sorted(list(set(dev_origins)))

    # 5. DEFAULT FAIL-CLOSED (Unknown or Contradictory settings):
    # Localhost is strictly prohibited.
    return sorted(list(set([o.rstrip("/") for o in raw_custom if is_valid_production_origin(o)])))

