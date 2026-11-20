import logging
import json
import re
import sys
from datetime import datetime, timezone
from contextvars import ContextVar
from typing import Optional, Any, Dict

# Context variable for request correlation ID
correlation_id_ctx: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)

# Redaction patterns for sensitive data (tokens, passwords, API keys, reproductive health answers)
REDACT_KEYS = {
    "password", "hashed_password", "token", "access_token", "secret", "secret_key",
    "authorization", "api_key", "credentials", "answer_value", "response_value_json"
}

REDACT_PATTERNS = [
    (re.compile(r'(Bearer\s+)[A-Za-z0-9\-\._~\+\/]+=*', re.IGNORECASE), r'\1[REDACTED_TOKEN]'),
    (re.compile(r'("password"\s*:\s*")[^"]+(")', re.IGNORECASE), r'\1[REDACTED_PASSWORD]\2'),
    (re.compile(r'("access_token"\s*:\s*")[^"]+(")', re.IGNORECASE), r'\1[REDACTED_TOKEN]\2'),
    (re.compile(r'("secret(?:_key)?"\s*:\s*")[^"]+(")', re.IGNORECASE), r'\1[REDACTED_SECRET]\2'),
]

def sanitize_dict(data: Any) -> Any:
    """Recursively sanitizes dictionary keys and string values to prevent sensitive data leakage."""
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            if str(k).lower() in REDACT_KEYS:
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_dict(v)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_dict(item) for item in data]
    elif isinstance(data, str):
        val = data
        for pattern, replacement in REDACT_PATTERNS:
            val = pattern.sub(replacement, val)
        return val
    return data

class StructuredJsonFormatter(logging.Formatter):
    """
    Enterprise-grade JSON Formatter for centralized application logging.
    Enforces log levels: DEBUG, INFO, WARN, ERROR, FATAL.
    Outputs standardized schema: timestamp, level, service, correlation_id, message, extra.
    """
    def format(self, record: logging.LogRecord) -> str:
        level_name = record.levelname
        if level_name == "WARNING":
            level_name = "WARN"
        elif level_name == "CRITICAL":
            level_name = "FATAL"

        log_payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level_name,
            "service": "GENOVEX_BACKEND",
            "module": record.name,
            "correlation_id": correlation_id_ctx.get() or getattr(record, "correlation_id", "N/A"),
            "message": record.getMessage()
        }

        # Handle exception tracebacks safely
        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        # Merge extra attributes if provided
        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            log_payload["extra"] = sanitize_dict(record.extra_fields)

        # Sanitize entire log payload
        sanitized_payload = sanitize_dict(log_payload)
        return json.dumps(sanitized_payload, ensure_ascii=False)

def setup_logging(log_level: str = "INFO"):
    """Configures root logger with the StructuredJsonFormatter."""
    root_logger = logging.getLogger()
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJsonFormatter())
    root_logger.addHandler(handler)

    # Reduce noisy third-party logs
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("passlib").setLevel(logging.ERROR)

def get_logger(name: str) -> logging.Logger:
    """Returns a named logger configured for structured logging."""
    return logging.getLogger(name)
