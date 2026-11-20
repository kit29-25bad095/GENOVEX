# GENOVEX Monitoring & Centralized Logging Specification

## 1. Health Monitoring Subsystem

The GENOVEX platform provides a multi-tier health monitoring architecture designed to support Kubernetes readiness/liveness probes, AWS/Azure Application Load Balancers, Cloudflare health checks, and internal clinical diagnostic dashboards.

### 1.1 Public Health Endpoints
- **Endpoints:** `GET /api/health` and `GET /health`
- **Access Level:** Public / Unauthenticated
- **Primary Function:** Ingress uptime checks, load-balancer routing, zero-downtime deployment health validation.
- **Security Boundary:** Strictly sanitizes and strips all internal system secrets, credentials, database paths, and user details.
- **HTTP Status Codes:**
  - `200 OK`: Database connected, system healthy or degraded.
  - `503 Service Unavailable`: Core database connection failure.

#### Example Payload:
```json
{
  "status": "healthy",
  "platform": "GENOVEX",
  "version": "1.0.0",
  "timestamp": "2026-11-20T20:30:00Z",
  "services": {
    "database": "healthy"
  }
}
```

### 1.2 Administrative Diagnostic Endpoint
- **Endpoint:** `GET /api/v1/admin/health/diagnostics`
- **Access Level:** Gated by RBAC (`ADMIN`, `SUPERADMIN`, `CLINICIAN`).
- **Telemetry Reported:**
  - Database ping latency (`latency_ms`)
  - Storage availability (`free_disk_mb`, `low_disk_warning`)
  - Subsystem operational status
  - AI circuit breaker state

---

## 2. Centralized Structured Logging

### 2.1 JSON Schema Specification
All application logs are formatted as single-line JSON objects conforming to the following structure:

```json
{
  "timestamp": "2026-11-20T20:31:05.123456Z",
  "level": "INFO",
  "logger": "genovex_main",
  "message": "POST /api/v1/assessment/start responded 200 in 14.2ms (IP: 192.168.1.10)",
  "correlation_id": "c1f7b8e2-892d-4f11-9a74-b520489c7d41",
  "extra_fields": {
    "method": "POST",
    "path": "/api/v1/assessment/start",
    "status_code": 200,
    "duration_ms": 14.2,
    "client_ip": "192.168.1.10"
  }
}
```

### 2.2 Standard Log Levels
- **`DEBUG`**: Detailed diagnostic traces for developer troubleshooting. Disabled in UAE production environments.
- **`INFO`**: Normal operational events (e.g., successful evaluations, backup creations, user logins).
- **`WARN` / `WARNING`**: Degraded performance, single API timeouts, or circuit breaker state transitions.
- **`ERROR`**: Caught operational exceptions, database query timeouts, or third-party service failures.
- **`FATAL`**: Application startup failures or unrecoverable storage crashes.

---

## 3. Correlation ID Propagation (`X-Correlation-ID`)

Every incoming HTTP request is intercepted by the correlation middleware:
1. Checks for incoming `X-Correlation-ID` header. If absent, generates an RFC 4122 UUID v4.
2. Sets the ID in Python `contextvars.ContextVar` (`correlation_id_ctx`) for thread/async isolation.
3. Automatically injects `X-Correlation-ID` into the response headers.
4. Includes the correlation ID in every log line and standardized error payload.

---

## 4. Sensitive Data Sanitization & PII Redaction

Under UAE Federal Decree-Law No. 45 of 2021 regarding Personal Data Protection and healthcare compliance regulations, the logging engine intercepts dictionary parameters and sanitizes values:

- **Redacted Field Patterns:** `*password*`, `*token*`, `*secret*`, `*auth*`, `*key*`, `*answer*`, `*symptom*`, `*response*`
- **Masking Mechanism:** Values matching pattern keys are immediately replaced with string literal `"[REDACTED]"`.
- **Pre-serialization Enforcement:** Logging filters operate at formatter output time, preventing plaintext persistence to log aggregators (e.g., Datadog, AWS CloudWatch, ELK).
