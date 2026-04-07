from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pathlib import Path

router = APIRouter()

HTML_FILE = Path("sites/root/index.html")

@router.get("/", response_class=HTMLResponse)
async def root_page():
    return HTML_FILE.read_text()