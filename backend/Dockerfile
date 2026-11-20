# =============================================================================
# GENOVEX Backend Production Dockerfile (Python 3.11 Slim)
# =============================================================================

# Stage 1: Build & wheels generation
FROM python:3.11-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt

# Stage 2: Minimal hardened production runtime
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    HOST=0.0.0.0 \
    ENVIRONMENT=production

# Install runtime utilities (curl for container healthcheck, sqlite3 for DB diagnostics)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install wheels from builder stage
COPY --from=builder /build/wheels /wheels
COPY --from=builder /build/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir /wheels/* \
    && rm -rf /wheels

# Create dedicated non-root application user
RUN groupadd -g 1001 genovex \
    && useradd -u 1001 -g genovex -s /bin/bash -m genovex

# Create storage directories with proper ownership
RUN mkdir -p /app/data /app/backups \
    && chown -R genovex:genovex /app

# Copy application source code
COPY --chown=genovex:genovex . /app/

# Switch to non-root execution
USER genovex

EXPOSE 8000

# Container healthcheck querying liveness endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://127.0.0.1:8000/health/live || exit 1

# Production startup using Gunicorn with Uvicorn workers
CMD ["gunicorn", "-c", "gunicorn_conf.py", "main:app"]
