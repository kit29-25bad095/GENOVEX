import os
import time
import uuid
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.core.logging_config import setup_logging, get_logger, correlation_id_ctx
from app.core.scheduler import MaintenanceScheduler
from app.core.seed_data import seed_database
from app.core.seed_questionnaire import seed_questionnaire_v1
from app.core.seed_clinical_rules import seed_clinical_rules_v1

# Route imports
from app.api.v1.endpoints.auth import router as auth_router, audit_router
from app.api.v1.endpoints.admin_medical_content import router as admin_medical_content_router
from app.api.v1.endpoints.public_health_library import router as public_health_library_router
from app.api.v1.endpoints.questionnaire import router as questionnaire_router
from app.api.v1.endpoints.admin_questionnaire import router as admin_questionnaire_router
from app.api.v1.endpoints.assessment_evaluation import router as assessment_evaluation_router
from app.api.v1.endpoints.admin_clinical_rules import router as admin_clinical_rules_router
from app.api.v1.endpoints.ai import router as ai_router
from app.api.v1.endpoints.clinician import router as clinician_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.admin_maintenance import router as admin_maintenance_router

# Initialize structured logging
setup_logging(settings.LOG_LEVEL)
logger = get_logger("genovex_main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure tables exist and seed default content
    logger.info("Initializing GENOVEX application tables and seed baselines...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
        seed_questionnaire_v1(db)
        seed_clinical_rules_v1(db)
    finally:
        db.close()

    # Start background maintenance scheduler
    await MaintenanceScheduler.start()
    yield
    # Shutdown
    await MaintenanceScheduler.stop()
    logger.info("GENOVEX application shutdown complete.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="GENOVEX AI-Assisted Male Reproductive Health Platform API",
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# CORS configuration with environment-driven precedence
from app.core.config import get_allowed_cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Phase 17: Production Security Headers Middleware
# -----------------------------------------------------------------------------
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if settings.ENVIRONMENT.lower() in ("production", "staging"):
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    return response

# -----------------------------------------------------------------------------
# Module B & C: Request Tracing, Correlation ID & Structured Logging Middleware
# -----------------------------------------------------------------------------
@app.middleware("http")
async def correlation_and_logging_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID") or f"gnx_{uuid.uuid4().hex[:12]}"
    correlation_id_ctx.set(correlation_id)

    start_time = time.perf_counter()
    client_ip = request.client.host if request.client else "unknown"

    try:
        response = await call_next(request)
        process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Correlation-ID"] = correlation_id

        # Log request summary safely without recording credentials or questionnaire data
        if not request.url.path.startswith("/static"):
            logger.info(
                f"{request.method} {request.url.path} responded {response.status_code} in {process_time_ms}ms (IP: {client_ip})",
                extra={
                    "extra_fields": {
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "duration_ms": process_time_ms,
                        "client_ip": client_ip,
                        "correlation_id": correlation_id
                    }
                }
            )
        return response
    except Exception as e:
        process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.error(
            f"Unhandled exception on {request.method} {request.url.path}: {str(e)}",
            exc_info=True,
            extra={
                "extra_fields": {
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": process_time_ms,
                    "client_ip": client_ip,
                    "correlation_id": correlation_id
                }
            }
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred. Please contact system support with your correlation ID.",
                    "correlation_id": correlation_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            },
            headers={"X-Correlation-ID": correlation_id}
        )

# -----------------------------------------------------------------------------
# Module C: Standardized API Error Handlers
# -----------------------------------------------------------------------------
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    cid = correlation_id_ctx.get() or "N/A"
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "correlation_id": cid,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        },
        headers={"X-Correlation-ID": cid}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    cid = correlation_id_ctx.get() or "N/A"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request parameters or payload format",
                "details": exc.errors(),
                "correlation_id": cid,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        },
        headers={"X-Correlation-ID": cid}
    )

# -----------------------------------------------------------------------------
# Include API Routers
# -----------------------------------------------------------------------------
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(audit_router, prefix=settings.API_V1_STR)
app.include_router(admin_medical_content_router, prefix=settings.API_V1_STR)
app.include_router(public_health_library_router, prefix=settings.API_V1_STR)
app.include_router(questionnaire_router, prefix=settings.API_V1_STR)
app.include_router(admin_questionnaire_router, prefix=settings.API_V1_STR)
app.include_router(assessment_evaluation_router, prefix=settings.API_V1_STR)
app.include_router(admin_clinical_rules_router, prefix=settings.API_V1_STR)
app.include_router(ai_router, prefix=settings.API_V1_STR)
app.include_router(clinician_router, prefix=settings.API_V1_STR)
app.include_router(admin_maintenance_router, prefix=settings.API_V1_STR)

# Health router mounted at both /api/health and /health
app.include_router(health_router, prefix="/api")
app.include_router(health_router)

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "app", "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# -----------------------------------------------------------------------------
# Interactive Web Application Routes
# -----------------------------------------------------------------------------
@app.get("/admin/medical-content", response_class=HTMLResponse, tags=["Web UI"])
def admin_medical_content_ui():
    """Serves the Admin Medical Content Management Dashboard"""
    admin_html_path = os.path.join(static_dir, "admin_medical_content.html")
    if os.path.exists(admin_html_path):
        with open(admin_html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h3>Admin Dashboard Template Loading...</h3>")

@app.get("/health-library", response_class=HTMLResponse, tags=["Web UI"])
def public_health_library_ui():
    """Serves the Public Health Library Portal"""
    library_html_path = os.path.join(static_dir, "public_health_library.html")
    if os.path.exists(library_html_path):
        with open(library_html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h3>Public Health Library Loading...</h3>")

@app.get("/admin/clinical-rules", response_class=HTMLResponse, tags=["Web UI"])
def admin_clinical_rules_ui():
    """Serves the Clinical Rule Governance Dashboard"""
    rules_html_path = os.path.join(static_dir, "admin_clinical_rules.html")
    if os.path.exists(rules_html_path):
        with open(rules_html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h3>Clinical Rule Dashboard Loading...</h3>")

@app.get("/assessment", response_class=HTMLResponse, tags=["Web UI"])
def adaptive_questionnaire_ui():
    """Serves the Patient Adaptive Questionnaire Assessment Portal"""
    q_html_path = os.path.join(static_dir, "adaptive_questionnaire.html")
    if os.path.exists(q_html_path):
        with open(q_html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h3>Adaptive Questionnaire Portal Loading...</h3>")

@app.get("/", response_class=HTMLResponse, tags=["Web UI"])
def home_redirect():
    """Landing redirect to Health Library, Admin, or Assessment"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>GENOVEX — Male Reproductive Health Platform</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Manrope:wght@600;700;800&family=Noto+Sans+Arabic:wght@400;600;700&display=swap" rel="stylesheet">
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body { font-family: 'Inter', sans-serif; background-color: #F5F8FA; color: #20313F; }
            .font-heading { font-family: 'Manrope', sans-serif; }
        </style>
    </head>
    <body class="min-h-screen flex flex-col justify-between">
        <header class="bg-[#153B55] text-white py-4 px-6 shadow-sm border-b border-[#0E273A]">
            <div class="max-w-6xl mx-auto flex items-center justify-between">
                <div class="flex items-center space-x-3">
                    <div class="w-10 h-10 rounded-lg bg-[#159A91] flex items-center justify-center font-bold text-xl tracking-wider">G</div>
                    <div>
                        <span class="font-heading font-extrabold text-2xl tracking-tight">GENOVEX</span>
                        <span class="text-xs block text-teal-200 tracking-wider uppercase font-semibold">Male Reproductive Health • UAE</span>
                    </div>
                </div>
                <div class="flex items-center space-x-4 text-sm font-medium">
                    <a href="/assessment" class="bg-[#159A91] hover:bg-teal-600 px-3.5 py-1.5 rounded-lg text-white font-semibold transition">Start Assessment</a>
                    <a href="/health-library" class="hover:text-teal-300 transition">Health Library</a>
                    <a href="/admin/medical-content" class="hover:text-teal-300 transition">Admin CMS</a>
                    <a href="/admin/clinical-rules" class="hover:text-teal-300 transition">Rules Registry</a>
                    <a href="/api/health" target="_blank" class="text-teal-300 hover:text-white transition">Health API ↗</a>
                    <a href="/docs" target="_blank" class="text-gray-300 hover:text-white transition">Swagger API</a>
                </div>
            </div>
        </header>

        <main class="max-w-6xl mx-auto px-6 py-12 flex-1 flex flex-col justify-center">
            <div class="text-center mb-12">
                <div class="inline-flex items-center space-x-2 bg-teal-50 border border-teal-200 text-[#159A91] px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider mb-4">
                    <span>GENOVEX Platform • Reliability & Maintenance Ready (Phase 18)</span>
                </div>
                <h1 class="text-4xl md:text-5xl font-heading font-extrabold text-[#153B55] mb-4">
                    Male Reproductive Health Risk Identification & Navigation
                </h1>
                <p class="text-lg text-gray-600 max-w-2xl mx-auto">
                    Evidence-informed digital platform for the UAE. Features an 11-domain adaptive questionnaire, deterministic safety triage, and dynamic bilingual clinical knowledge governance.
                </p>
            </div>

            <div class="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
                <!-- Card 1: Adaptive Questionnaire -->
                <div class="bg-white rounded-2xl p-6 border-2 border-[#159A91] shadow-sm hover:shadow-md transition flex flex-col justify-between">
                    <div>
                        <div class="w-12 h-12 rounded-xl bg-teal-50 text-[#159A91] flex items-center justify-center mb-4">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"></path></svg>
                        </div>
                        <h2 class="text-xl font-heading font-bold text-[#153B55] mb-2">Adaptive Assessment</h2>
                        <p class="text-xs text-gray-600 mb-6 leading-relaxed">
                            Structured 11-domain health questionnaire with dynamic branching, priority safety red-flags, and verified clinical reports.
                        </p>
                    </div>
                    <a href="/assessment" class="w-full text-center bg-[#159A91] hover:bg-teal-700 text-white font-semibold py-2.5 px-4 rounded-xl transition shadow-sm text-sm">
                        Launch Assessment →
                    </a>
                </div>

                <!-- Card 2: Admin & Clinical Governance -->
                <div class="bg-white rounded-2xl p-6 border border-[#E4EBF0] shadow-sm hover:shadow-md transition flex flex-col justify-between">
                    <div>
                        <div class="w-12 h-12 rounded-xl bg-blue-50 text-[#153B55] flex items-center justify-center mb-4">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"></path></svg>
                        </div>
                        <h2 class="text-xl font-heading font-bold text-[#153B55] mb-2">Clinical Governance</h2>
                        <p class="text-xs text-gray-600 mb-6 leading-relaxed">
                            Medical content CMS and deterministic clinical rules registry with version rollback, audit trail, and clinician sign-off.
                        </p>
                    </div>
                    <a href="/admin/clinical-rules" class="w-full text-center bg-[#153B55] hover:bg-[#0E273A] text-white font-semibold py-2.5 px-4 rounded-xl transition shadow-sm text-sm">
                        Clinical Rules Registry →
                    </a>
                </div>

                <!-- Card 3: Public Health Library -->
                <div class="bg-white rounded-2xl p-6 border border-[#E4EBF0] shadow-sm hover:shadow-md transition flex flex-col justify-between">
                    <div>
                        <div class="w-12 h-12 rounded-xl bg-teal-50 text-[#159A91] flex items-center justify-center mb-4">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path></svg>
                        </div>
                        <h2 class="text-xl font-heading font-bold text-[#153B55] mb-2">Public Health Library</h2>
                        <p class="text-xs text-gray-600 mb-6 leading-relaxed">
                            Bilingual clinical knowledge base populated from verified international guidelines (WHO, EAU, AUA).
                        </p>
                    </div>
                    <a href="/health-library" class="w-full text-center bg-gray-100 hover:bg-gray-200 text-[#153B55] font-semibold py-2.5 px-4 rounded-xl transition shadow-sm text-sm">
                        Explore Health Library →
                    </a>
                </div>
            </div>
        </main>

        <footer class="bg-white border-t border-[#E4EBF0] py-6 text-center text-xs text-gray-500">
            <p>© 2026 GENOVEX Healthcare Platform • Evidence-Based Male Reproductive Health • Designed for UAE Regulatory Compliance</p>
        </footer>
    </body>
    </html>
    """)
