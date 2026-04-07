from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pathlib import Path

router = APIRouter()

HTML_FILE = Path("sites/pagenotfound/404.html")

@router.get("/404", response_class=HTMLResponse)
async def not_found_page():
    return HTML_FILE.read_text()