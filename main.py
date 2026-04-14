import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

from api import explore as exploreapi
from api import login as loginapi
from api import messages as messagesapi
from api import profiles as profilesapi
from api import projects as projectsapi
from api import register as registerapi
from api import session as sessionapi
from core import app_paths
from core.logger import configure_logging, get_logger
from core.rate_limit import limiter
from pages import page_not_found_html
from routes import (
    dashboard,
    explore,
    login,
    pagenotfound,
    project,
    register,
    root,
    user_profile,
)
from utils.repository_manager_util import setup_start

configure_logging()
logger = get_logger(__name__)
MAX_REQUEST_SIZE_BYTES = int(os.getenv("MAX_REQUEST_SIZE_BYTES", str(26 * 1024 * 1024)))
CORS_ALLOW_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOW_ORIGINS",
        "http://127.0.0.1:8000,http://localhost:8000",
    ).split(",")
    if origin.strip()
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    from core.database import Base, engine

    logger.info("Starting application")
    setup_start(app_paths.DATA_ROOT)
    # Tests provide their own in-memory database and should not touch Database.db.
    if "pytest" in sys.modules:
        logger.debug("Skipping production database initialization during tests")
    else:
        Base.metadata.create_all(bind=engine)
        logger.debug("Database tables ensured")
    yield
    logger.info("Stopping application")


app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def rate_limit_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.warning("Rate limit exceeded for %s %s", request.method, request.url.path)
    return JSONResponse({"detail": "Too many requests, slow down."}, status_code=429)


app.add_exception_handler(RateLimitExceeded, rate_limit_handler)


# ================================
# Mount static files per page
# ================================
BASE_DIR = os.path.dirname(__file__)

app.mount(
    "/root",
    StaticFiles(directory=os.path.join(BASE_DIR, "sites/root")),
    name="root_static",
)
app.mount(
    "/login",
    StaticFiles(directory=os.path.join(BASE_DIR, "sites/login")),
    name="login_static",
)
app.mount(
    "/register",
    StaticFiles(directory=os.path.join(BASE_DIR, "sites/register")),
    name="register_static",
)
app.mount(
    "/dashboard",
    StaticFiles(directory=os.path.join(BASE_DIR, "sites/dashboard")),
    name="dashboard_static",
)
app.mount(
    "/explore-assets",
    StaticFiles(directory=os.path.join(BASE_DIR, "sites/explore")),
    name="explore_assets",
)
app.mount(
    "/user-assets",
    StaticFiles(directory=os.path.join(BASE_DIR, "sites/user")),
    name="user_assets",
)
app.mount(
    "/repository-assets",
    StaticFiles(directory=os.path.join(BASE_DIR, "sites/project")),
    name="repository_assets",
)

# ================================
# Include routers
# ================================
app.include_router(root.router)
app.include_router(pagenotfound.router)
app.include_router(register.router)
app.include_router(login.router)
app.include_router(dashboard.router)
app.include_router(explore.router)
app.include_router(user_profile.router)
app.include_router(project.router)

app.include_router(registerapi.router, prefix="/api", tags=["Register"])
app.include_router(loginapi.router, prefix="/api", tags=["Login"])
app.include_router(sessionapi.router, prefix="/api", tags=["Session"])
app.include_router(projectsapi.router, prefix="/api", tags=["Repositories"])
app.include_router(exploreapi.router, prefix="/api", tags=["Explore"])
app.include_router(profilesapi.router, prefix="/api", tags=["Profiles"])
app.include_router(messagesapi.router, prefix="/api", tags=["Messages"])


@app.middleware("http")
async def reject_large_requests(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_REQUEST_SIZE_BYTES:
                return JSONResponse(
                    {"detail": "Request body too large"},
                    status_code=413,
                )
        except ValueError:
            return JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)
    return await call_next(request)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), "
        "payment=(), usb=(), interest-cohort=()"
    )
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    )
    return response


# ================================
# Global 404 handler
# ================================
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    logger.info("Route not found: %s %s", request.method, request.url.path)
    return HTMLResponse(content=page_not_found_html, status_code=404)


# ================================
# Run the app
# ================================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        h11_max_incomplete_event_size=MAX_REQUEST_SIZE_BYTES,
    )
