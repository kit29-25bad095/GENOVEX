import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import enum

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("ai_monitoring_service")

class CircuitState(str, enum.Enum):
    CLOSED = "CLOSED"       # Normal operations: requests flow through
    OPEN = "OPEN"           # Tripped: requests immediately fail to fallback
    HALF_OPEN = "HALF_OPEN" # Recovery testing: trial requests allowed

class AIMonitoringService:
    """
    Operational monitoring, circuit-breaker, and fallback reliability engine for AI integrations.
    Protects GENOVEX from external AI latency spikes, rate limits, and outages.
    Guarantees that AI failures never compromise deterministic clinical safety rules.
    """

    # In-memory operational telemetry state
    _circuit_state: CircuitState = CircuitState.CLOSED
    _failure_count: int = 0
    _consecutive_successes: int = 0
    _last_failure_time: Optional[float] = None
    _total_requests: int = 0
    _total_failures: int = 0
    _total_timeouts: int = 0
    _total_rate_limits: int = 0
    _total_tokens_used: int = 0
    _estimated_cost_usd: float = 0.0
    _average_latency_ms: float = 0.0

    @classmethod
    def get_circuit_state(cls) -> CircuitState:
        """Evaluates circuit state with automatic cooldown transition to HALF_OPEN."""
        if cls._circuit_state == CircuitState.OPEN:
            cooldown = settings.AI_CIRCUIT_BREAKER_COOLDOWN_SEC
            if cls._last_failure_time and (time.time() - cls._last_failure_time) > cooldown:
                cls._circuit_state = CircuitState.HALF_OPEN
                logger.info("AI Circuit Breaker cooldown elapsed. Transitioning from OPEN to HALF_OPEN.")
        return cls._circuit_state

    @classmethod
    def record_request_attempt(cls):
        cls._total_requests += 1

    @classmethod
    def record_success(cls, latency_ms: float, tokens_consumed: int = 0, cost_estimate: float = 0.0):
        cls._failure_count = 0
        cls._consecutive_successes += 1
        cls._total_tokens_used += tokens_consumed
        cls._estimated_cost_usd += cost_estimate

        # Moving average latency
        if cls._average_latency_ms == 0:
            cls._average_latency_ms = latency_ms
        else:
            cls._average_latency_ms = round((cls._average_latency_ms * 0.9) + (latency_ms * 0.1), 2)

        if cls._circuit_state == CircuitState.HALF_OPEN and cls._consecutive_successes >= 2:
            cls._circuit_state = CircuitState.CLOSED
            logger.info("AI Provider recovery verified. Circuit breaker closed.")

    @classmethod
    def record_failure(cls, error_type: str = "general_error", latency_ms: float = 0.0):
        cls._total_failures += 1
        cls._failure_count += 1
        cls._consecutive_successes = 0
        cls._last_failure_time = time.time()

        if error_type == "timeout":
            cls._total_timeouts += 1
        elif error_type == "rate_limit":
            cls._total_rate_limits += 1

        logger.warning(f"AI Provider failure recorded: {error_type}. Consecutive failures: {cls._failure_count}")

        if cls._failure_count >= settings.AI_CIRCUIT_BREAKER_MAX_FAILURES:
            cls._circuit_state = CircuitState.OPEN
            logger.error(
                f"AI Provider failure threshold exceeded ({cls._failure_count}/{settings.AI_CIRCUIT_BREAKER_MAX_FAILURES}). "
                "Circuit breaker tripped to OPEN. Fallback activated."
            )

    @classmethod
    def execute_with_circuit_breaker(cls, call_fn, fallback_fn=None, *args, **kwargs) -> Any:
        """
        Executes an AI operation guarded by circuit breaker and timeout.
        If circuit is OPEN or operation fails, falls back gracefully without breaking deterministic logic.
        """
        current_state = cls.get_circuit_state()
        if current_state == CircuitState.OPEN:
            logger.warning("AI Circuit Breaker is OPEN. Executing safe fallback immediately.")
            if fallback_fn:
                return fallback_fn(*args, **kwargs)
            return None

        cls.record_request_attempt()
        start = time.perf_counter()
        try:
            result = call_fn(*args, **kwargs)
            latency = (time.perf_counter() - start) * 1000
            cls.record_success(latency_ms=latency)
            return result
        except TimeoutError:
            latency = (time.perf_counter() - start) * 1000
            cls.record_failure(error_type="timeout", latency_ms=latency)
            if fallback_fn:
                return fallback_fn(*args, **kwargs)
            return None
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            err_str = str(e).lower()
            err_type = "rate_limit" if "429" in err_str or "quota" in err_str else "api_error"
            cls.record_failure(error_type=err_type, latency_ms=latency)
            if fallback_fn:
                return fallback_fn(*args, **kwargs)
            return None

    @classmethod
    def get_telemetry_summary(cls) -> Dict[str, Any]:
        """Returns sanitized operational metrics for monitoring dashboards without secrets."""
        return {
            "circuit_breaker_state": cls.get_circuit_state().value,
            "consecutive_failures": cls._failure_count,
            "total_requests": cls._total_requests,
            "total_failures": cls._total_failures,
            "total_timeouts": cls._total_timeouts,
            "total_rate_limits": cls._total_rate_limits,
            "average_latency_ms": round(cls._average_latency_ms, 2),
            "total_tokens_consumed": cls._total_tokens_used,
            "estimated_cost_usd": round(cls._estimated_cost_usd, 4),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    @classmethod
    def reset_circuit(cls):
        """Manual administrative reset of circuit breaker."""
        cls._circuit_state = CircuitState.CLOSED
        cls._failure_count = 0
        cls._consecutive_successes = 0
        cls._last_failure_time = None
        logger.info("AI Circuit breaker manually reset to CLOSED.")
