import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from api import login as loginapi
from api import register as registerapi
from api import session as sessionapi
from pages import page_not_found_html
from routes import dashboard, login, pagenotfound, register, root

limiter = Limiter(key_func=get_remote_address, default_limits=[])


@asynccontextmanager
async def lifespan(app: FastAPI):
    from database import Base, engine

    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter


async def rate_limit_handler(request: Request, exc: Exception) -> JSONResponse:
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

# ================================
# Include routers
# ================================
app.include_router(root.router)
app.include_router(pagenotfound.router)
app.include_router(register.router)
app.include_router(login.router)
app.include_router(dashboard.router)

app.include_router(registerapi.router, prefix="/api", tags=["Register"])
app.include_router(loginapi.router, prefix="/api", tags=["Login"])
app.include_router(sessionapi.router, prefix="/api", tags=["Session"])


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
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
    return HTMLResponse(content=page_not_found_html, status_code=404)


# ================================
# Run the app
# ================================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
