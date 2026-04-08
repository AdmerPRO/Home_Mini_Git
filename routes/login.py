from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pages import login_html

router = APIRouter()

@router.get("/login", response_class=HTMLResponse)
async def login_page():
    return login_html
