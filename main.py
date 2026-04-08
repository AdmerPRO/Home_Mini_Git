from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pages import page_not_found_html
from routes import root, pagenotfound, login, register
from api import login as loginapi, register as registerapi
import os

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter

async def rate_limit_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse({"detail": "Too many requests, slow down."}, status_code=429)

app.add_exception_handler(RateLimitExceeded, rate_limit_handler)  # type: ignore[arg-type]

# ================================
# Mount static files per page
# ================================
BASE_DIR = os.path.dirname(__file__)

app.mount("/root",         StaticFiles(directory=os.path.join(BASE_DIR, "sites/root")),        name="root_static")
app.mount("/pagenotfound", StaticFiles(directory=os.path.join(BASE_DIR, "sites/pagenotfound")),name="404_static")
app.mount("/login",        StaticFiles(directory=os.path.join(BASE_DIR, "sites/login")),       name="login_static")
app.mount("/register",     StaticFiles(directory=os.path.join(BASE_DIR, "sites/register")),    name="register_static")

# ================================
# Include routers
# ================================
app.include_router(root.router)
app.include_router(pagenotfound.router)
app.include_router(register.router)
app.include_router(login.router)

app.include_router(registerapi.router, prefix="/api", tags=["Register"])
app.include_router(loginapi.router,    prefix="/api", tags=["Login"])

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
