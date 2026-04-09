from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from pages import register_html

router = APIRouter()


@router.get("/register", response_class=HTMLResponse)
async def register_page():
    return register_html
