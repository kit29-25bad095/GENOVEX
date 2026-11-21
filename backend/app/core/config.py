import os
import re
import ipaddress
from pathlib import Path
from urllib.parse import urlparse
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Authoritative repository root & database path resolution
PROJECT_ROOT = Path(__file__).resolve().parents[3]
AUTHORITATIVE_DB_PATH = PROJECT_ROOT / "genovex.db"

def is_sqlite_path_absolute(path_str: str) -> bool:
    """Check if a path string is an absolute path across Windows (e.g. C:/...) and POSIX (/...)."""
    if not path_str:
        return False
    norm = path_str.replace("\\", "/")
    if norm.startswith("/") or norm.startswith("//"):
        return True
    if len(norm) >= 2 and norm[0].isalpha() and norm[1] == ":":
        return True
    try:
        return Path(norm).is_absolute()
    except Exception:
        return False

def normalize_database_url(
    raw_url: Optional[str],
    environment: str,
    base_dir: Path = PROJECT_ROOT
) -> str:
    """
    Normalizes and validates a database connection URL.
    - Prevents silent fallback to development SQLite in production and staging.
    - Resolves relative SQLite paths deterministically relative to PROJECT_ROOT regardless of CWD.
    - Ensures parent directories exist for file-based SQLite databases.
    - Standardizes URL formatting for SQLAlchemy 2.0 (e.g., postgresql://).
    """
    env_clean = (environment or "development").strip().lower()
    vercel_env = (os.getenv("VERCEL_ENV") or "").strip().lower()
    is_prod_env = env_clean in ("production", "staging") or vercel_env in ("production", "staging")

    if not raw_url or not raw_url.strip():
        if is_prod_env:
            raise ValueError(
                f"CRITICAL CONFIGURATION ERROR: DATABASE_URL must be explicitly configured in {env_clean} environment! "
                "Fallback to development SQLite database is strictly prohibited."
            )
        return f"sqlite:///{AUTHORITATIVE_DB_PATH.as_posix()}"

    url = raw_url.strip()
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ValueError(f"CRITICAL CONFIGURATION ERROR: Malformed DATABASE_URL: {e}")

    scheme = parsed.scheme.lower()

    if scheme in ("postgresql", "postgres"):
        if scheme == "postgres":
            url = "postgresql" + url[len("postgres"):]
        return url

    if scheme == "sqlite":
        url_body = url[len("sqlite:"):]
        query_part = ""
        if "?" in url_body:
            url_body, query_part = url_body.split("?", 1)
            query_part = "?" + query_part

        norm_body = url_body.replace("\\", "/")
        from urllib.parse import unquote
        clean = unquote(norm_body.lstrip("/"))

        if clean.startswith(":memory:"):
            return f"sqlite:///:memory:{query_part}"

        if norm_body.startswith("///"):
            path_part = norm_body[3:]
        elif norm_body.startswith("//"):
            path_part = norm_body[2:]
        else:
            path_part = norm_body
        path_part = unquote(path_part)

        is_abs = is_sqlite_path_absolute(path_part)
        if is_abs:
            abs_path = Path(path_part).resolve()
        else:
            abs_path = (base_dir / path_part).resolve()

        if is_prod_env:
            try:
                if abs_path.samefile(AUTHORITATIVE_DB_PATH) or str(abs_path).lower() == str(AUTHORITATIVE_DB_PATH.resolve()).lower():
                    raise ValueError(
                        f"CRITICAL SECURITY ERROR: Binding to development database '{AUTHORITATIVE_DB_PATH.name}' "
                        f"is strictly prohibited in {env_clean} environment!"
                    )
            except (FileNotFoundError, OSError):
                pass
            if not is_abs:
                raise ValueError(
                    f"CRITICAL CONFIGURATION ERROR: Relative SQLite database path '{path_part}' "
                    f"is prohibited in {env_clean} environment. Use an absolute path or managed PostgreSQL URL."
                )

        try:
            abs_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ValueError(f"CRITICAL CONFIGURATION ERROR: Cannot create parent directory for database path '{abs_path}': {e}")

        return f"sqlite:///{abs_path.as_posix()}{query_part}"

    raise ValueError(
        f"CRITICAL CONFIGURATION ERROR: Unsupported database URL scheme '{scheme}'. "
        "Supported schemes: postgresql, sqlite."
    )

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
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
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

    # Phase 4: Authentication & Password Reset Configurations
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    RESET_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("RESET_TOKEN_EXPIRE_MINUTES", "15"))
    SMTP_HOST: Optional[str] = os.getenv("SMTP_HOST", None)
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: Optional[str] = os.getenv("SMTP_USER", None)
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD", None)
    SMTP_TLS: bool = os.getenv("SMTP_TLS", "True").lower() == "true"
    EMAILS_FROM_EMAIL: str = os.getenv("EMAILS_FROM_EMAIL", "noreply@genovex.health")
    TRUSTED_PROXIES: str = os.getenv("TRUSTED_PROXIES", "127.0.0.1,::1,testclient")

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

        # 3. Database URL normalization and safety validation across all environments
        raw_db_url = values.get("DATABASE_URL")
        if raw_db_url is None:
            raw_db_url = os.getenv("DATABASE_URL")
        if raw_db_url is None and self.DATABASE_URL:
            raw_db_url = self.DATABASE_URL

        self.DATABASE_URL = normalize_database_url(
            raw_url=raw_db_url,
            environment=self.ENVIRONMENT,
            base_dir=PROJECT_ROOT
        )

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

def is_ip_in_trusted_proxies(ip_str: str, trusted_config: str) -> bool:
    """Determines whether a client direct host matches configured trusted proxies or CIDR blocks."""
    if not ip_str:
        return False
    clean_ip = ip_str.strip().lower()
    if clean_ip in ("testclient", "testserver"):
        return True
    try:
        addr = ipaddress.ip_address(clean_ip)
    except ValueError:
        return False

    for item in (trusted_config or "").split(","):
        item = item.strip()
        if not item:
            continue
        if item.lower() in ("testclient", "testserver") and clean_ip in ("testclient", "testserver"):
            return True
        try:
            if "/" in item:
                network = ipaddress.ip_network(item, strict=False)
                if addr in network:
                    return True
            else:
                if addr == ipaddress.ip_address(item):
                    return True
        except ValueError:
            continue
    return False

def get_client_ip(request) -> str:
    """
    Extracts and validates the client IP address securely.
    - Rejects forwarding headers from untrusted direct peers.
    - Validates parsed IP addresses using ipaddress.ip_address.
    - Inspects X-Real-IP first when behind trusted reverse proxy.
    - Validates multi-hop X-Forwarded-For chains, rejecting malformed IPs.
    - Fails closed to direct peer IP on invalid/malformed headers.
    """
    if not request or not hasattr(request, "client") or not request.client:
        return "127.0.0.1"
    direct_ip = request.client.host

    # Check if direct peer is a trusted reverse proxy
    if not is_ip_in_trusted_proxies(direct_ip, settings.TRUSTED_PROXIES):
        try:
            ipaddress.ip_address(direct_ip)
            return direct_ip
        except ValueError:
            return "127.0.0.1"

    # Direct peer is trusted: inspect X-Real-IP first
    x_real_ip = request.headers.get("x-real-ip") or request.headers.get("X-Real-IP")
    if x_real_ip:
        candidate = x_real_ip.strip()
        try:
            ipaddress.ip_address(candidate)
            return candidate
        except ValueError:
            pass

    # Inspect X-Forwarded-For chain
    xff = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if xff:
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        valid_ips = []
        for part in parts:
            try:
                ipaddress.ip_address(part)
                valid_ips.append(part)
            except ValueError:
                continue
        if valid_ips:
            return valid_ips[0]

    return direct_ip


