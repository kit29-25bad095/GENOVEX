# =============================================================================
# GENOVEX Backend — Production Gunicorn Configuration
# =============================================================================
# Process management with Uvicorn worker class for high-throughput, fault-tolerant
# asynchronous API serving in production container environments (ECS / K8s).
# =============================================================================

import os
import multiprocessing

# Network binding
bind = f"{os.getenv('HOST', '0.0.0.0')}:{os.getenv('PORT', '8000')}"

# Concurrency & Worker model
# Formula: (2 x cores) + 1, or explicitly configured via WEB_CONCURRENCY
default_workers = max((2 * multiprocessing.cpu_count()) + 1, 2)
workers = int(os.getenv("WEB_CONCURRENCY", os.getenv("GUNICORN_WORKERS", default_workers)))
worker_class = "uvicorn.workers.UvicornWorker"

# Worker lifecycle & memory protection
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "2000"))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "100"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "60"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "30"))

# Logging
loglevel = os.getenv("LOG_LEVEL", "info").lower()
accesslog = "-"  # stdout
errorlog = "-"   # stderr
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" (%(D)s µs)'

# Server Mechanics
preload_app = False  # Avoid preloading when SQLite or connection pools need per-worker init
capture_output = True
enable_stdio_inheritance = True

def on_starting(server):
    server.log.info("Starting GENOVEX Production API Cluster...")

def post_fork(server, worker):
    server.log.info(f"Worker spawned (pid: {worker.pid})")

def worker_exit(server, worker):
    server.log.info(f"Worker exiting gracefully (pid: {worker.pid})")
