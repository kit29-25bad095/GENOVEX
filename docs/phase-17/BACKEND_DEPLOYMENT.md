# GENOVEX — Backend Deployment Specification

## 1. Application Runtime Architecture

The GENOVEX backend is a high-performance REST API built on **FastAPI** (Python 3.11), SQLAlchemy 2.0, Pydantic v2, and SQLite 3 WAL (migrating to managed PostgreSQL in Phase 14).

### 1.1 Process Management: Gunicorn + Uvicorn Workers
For high-concurrency production deployments, running raw `uvicorn main:app` is insufficient for fault tolerance and CPU utilization. GENOVEX utilizes **Gunicorn** as a master process manager managing multiple asynchronous **Uvicorn** worker processes (`uvicorn.workers.UvicornWorker`).

#### Master Configuration (`backend/gunicorn_conf.py`)
- **Worker Concurrency:** Calculated dynamically as `(2 * CPU cores) + 1` or controlled via `WEB_CONCURRENCY` / `GUNICORN_WORKERS`.
- **Worker Recycling:** `max_requests = 2000` with jitter of `100` to prevent memory leaks over sustained operational periods.
- **Graceful Termination:** `graceful_timeout = 30` seconds allows in-flight assessment evaluations and database transactions to commit prior to worker termination.
- **Worker Liveness:** Worker timeout set to `60` seconds with heartbeats.

---

## 2. Production Security & Middleware Stack

The HTTP request pipeline in `backend/main.py` is structured in strict order of execution:

```
[ Incoming Request ]
        │
        ▼
[ Security Headers Middleware ]
  - X-Content-Type-Options: nosniff
  - X-Frame-Options: DENY
  - X-XSS-Protection: 1; mode=block
  - Referrer-Policy: strict-origin-when-cross-origin
  - Permissions-Policy: camera=(), microphone=(), geolocation=()
  - Strict-Transport-Security (HSTS in production/staging)
        │
        ▼
[ Correlation ID & Tracing Middleware ]
  - Extracts or generates `X-Correlation-ID` (`gnx_<hex12>`)
  - Binds correlation ID to async ContextVar (`correlation_id_ctx`)
  - Structured request logging (excluding patient passwords/questionnaire secrets)
        │
        ▼
[ Strict CORS Middleware ]
  - Environment-driven allowed origins validation
  - Localhost strictly rejected in production and staging
        │
        ▼
[ API Routers & Exception Handlers ]
  - Standardized error envelopes with correlation ID tracking
```

---

## 3. Container Specification (`backend/Dockerfile`)

The backend container is built on a multi-stage `python:3.11-slim` image:

1. **Stage 1 (`builder`):**
   - Installs build essentials (`gcc`, `libpq-dev`, `curl`).
   - Compiles Python wheels for all dependencies listed in `backend/requirements.txt`.
2. **Stage 2 (`runner`):**
   - Hardened `python:3.11-slim` runtime.
   - Installs compiled wheels without leaving build tools or package managers in cache.
   - Creates unprivileged system user `genovex:genovex` (UID/GID 1001).
   - Pre-creates `/app/data` (for SQLite database storage) and `/app/backups` with `chown -R genovex:genovex`.
   - Runs as non-root user `genovex`.
   - Healthcheck: Probes `/health/live` every 30 seconds via `curl`.
   - Entrypoint: `gunicorn -c gunicorn_conf.py main:app`.

---

## 4. Health & Diagnostic Endpoints

The backend exposes four distinct health verification endpoints:

| Endpoint | HTTP Method | Target Consumers | Checks Performed |
| :--- | :--- | :--- | :--- |
| `/health` | `GET` | External load balancers, CDN edge | Lightweight service ping |
| `/health/live` | `GET` | Container runtime / Kubelet liveness | Process responsiveness |
| `/health/ready` | `GET` | Ingress controllers, deployment gates | Database connection, table readiness, scheduler status |
| `/health/detailed`| `GET` | SRE dashboards, internal monitoring | System metrics, database stats, disk space, backup health |

---

## 5. Deployment Commands & Verification

```bash
# 1. Build the production backend container image
docker build -t genovex-backend:latest ./backend

# 2. Run the container with mounted persistence
docker run -d \
  -p 8000:8000 \
  -v genovex_data:/app/data \
  -v genovex_backups:/app/backups \
  -e ENVIRONMENT=staging \
  -e SECRET_KEY="staging_secret_key_generate_with_secure_entropy_64chars_minimum_here" \
  -e ALLOW_SIMULATED_AUTH=False \
  -e CORS_ORIGINS="https://staging.genovex.ae" \
  --name genovex-backend-app \
  genovex-backend:latest

# 3. Check readiness
curl -I http://127.0.0.1:8000/health/ready
```
