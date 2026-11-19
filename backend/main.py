import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.core.seed_data import seed_database
from app.api.v1.endpoints.admin_medical_content import router as admin_medical_content_router
from app.api.v1.endpoints.public_health_library import router as public_health_library_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure tables exist and seed default content
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield
    # Shutdown

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="GENOVEX AI-Assisted Male Reproductive Health Platform API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(admin_medical_content_router, prefix=settings.API_V1_STR)
app.include_router(public_health_library_router, prefix=settings.API_V1_STR)

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "app", "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "online",
        "platform": "GENOVEX Digital Male Reproductive Health",
        "market": "UAE",
        "version": "1.0.0",
        "medical_module": "Dynamic Medical Content & Dysfunction Management"
    }

# Interactive Web Application Routes
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

@app.get("/", response_class=HTMLResponse, tags=["Web UI"])
def home_redirect():
    """Landing redirect to either Health Library or Admin Content Management"""
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
                    <a href="/health-library" class="hover:text-teal-300 transition">Health Library</a>
                    <a href="/admin/medical-content" class="bg-[#159A91] hover:bg-teal-600 px-4 py-2 rounded-lg text-white font-semibold transition">Admin CMS</a>
                    <a href="/docs" target="_blank" class="text-gray-300 hover:text-white transition">Swagger API</a>
                </div>
            </div>
        </header>

        <main class="max-w-5xl mx-auto px-6 py-12 flex-1 flex flex-col justify-center">
            <div class="text-center mb-12">
                <div class="inline-flex items-center space-x-2 bg-teal-50 border border-teal-200 text-[#159A91] px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider mb-4">
                    <span>Clinical Content & Dysfunction Management Module</span>
                </div>
                <h1 class="text-4xl md:text-5xl font-heading font-extrabold text-[#153B55] mb-4">
                    Dynamic Medical Knowledge & Dysfunction Engine
                </h1>
                <p class="text-lg text-gray-600 max-w-2xl mx-auto">
                    Evidence-informed male reproductive health management system for the UAE. Decoupled from assessment scoring, with strict clinical reviewer governance and dynamic bilingual publishing.
                </p>
            </div>

            <div class="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
                <!-- Card 1: Admin Module -->
                <div class="bg-white rounded-2xl p-8 border border-[#E4EBF0] shadow-sm hover:shadow-md transition flex flex-col justify-between">
                    <div>
                        <div class="w-12 h-12 rounded-xl bg-blue-50 text-[#153B55] flex items-center justify-center mb-4">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"></path></svg>
                        </div>
                        <h2 class="text-2xl font-heading font-bold text-[#153B55] mb-2">Admin Content Management</h2>
                        <p class="text-sm text-gray-600 mb-6 leading-relaxed">
                            Full lifecycle condition management: Add, edit, manage 20 structured clinical fields, review bilingual English & Arabic translations, approve, publish, archive, and rollback version history without changing application source code.
                        </p>
                    </div>
                    <a href="/admin/medical-content" class="w-full text-center bg-[#153B55] hover:bg-[#0E273A] text-white font-semibold py-3 px-6 rounded-xl transition shadow-sm">
                        Open Admin Dashboard →
                    </a>
                </div>

                <!-- Card 2: Public Health Library -->
                <div class="bg-white rounded-2xl p-8 border border-[#E4EBF0] shadow-sm hover:shadow-md transition flex flex-col justify-between">
                    <div>
                        <div class="w-12 h-12 rounded-xl bg-teal-50 text-[#159A91] flex items-center justify-center mb-4">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path></svg>
                        </div>
                        <h2 class="text-2xl font-heading font-bold text-[#153B55] mb-2">Public Health Library</h2>
                        <p class="text-sm text-gray-600 mb-6 leading-relaxed">
                            User-facing educational portal dynamically querying published medical conditions from the backend. Fully responsive with instant English (LTR) and Arabic (RTL) language switching, organ breakdowns, and evidence references.
                        </p>
                    </div>
                    <a href="/health-library" class="w-full text-center bg-[#159A91] hover:bg-teal-700 text-white font-semibold py-3 px-6 rounded-xl transition shadow-sm">
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
