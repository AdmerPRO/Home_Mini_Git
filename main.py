from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from routes import root, pagenotfound, login, register
from api import login as loginapi, register as registerapi
import os

app = FastAPI()

# ================================
# Mount static files per page
# ================================
BASE_DIR = os.path.dirname(__file__)

# Root page static files -> URL /root/
STATIC_ROOT = os.path.join(BASE_DIR, "sites/root")
app.mount("/root", StaticFiles(directory=STATIC_ROOT), name="root_static")

# 404 page static files -> URL /404/
STATIC_404 = os.path.join(BASE_DIR, "sites/pagenotfound")
app.mount("/pagenotfound", StaticFiles(directory=STATIC_404), name="404_static")

# Login page static files -> URL /login/
STATIC_LOGIN = os.path.join(BASE_DIR, "sites/login")
app.mount("/login", StaticFiles(directory=STATIC_LOGIN), name="login_static")

# Register page static files -> URL /register/
STATIC_REGISTER = os.path.join(BASE_DIR, "sites/register")
app.mount("/register", StaticFiles(directory=STATIC_REGISTER), name="register_static")

# ================================
# Include routers
# ================================
app.include_router(root.router)
app.include_router(pagenotfound.router)
app.include_router(register.router)
app.include_router(login.router)

app.include_router(registerapi.router, prefix="/api", tags=["Register"])
app.include_router(loginapi.router, prefix="/api", tags=["Login"])

# ================================
# Load 404 HTML for global 404 handler
# ================================
page_not_found_file = os.path.join(STATIC_404, "404.html")
with open(page_not_found_file, "r", encoding="utf-8") as f:
    page_not_found_html = f.read()

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