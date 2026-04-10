from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from pages import page_not_found_html

router = APIRouter()


@router.get("/pagenotfound", response_class=HTMLResponse)
async def not_found_page():
    return page_not_found_html
