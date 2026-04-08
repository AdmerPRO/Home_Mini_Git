from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pages import root_html

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def root_page():
    return root_html
