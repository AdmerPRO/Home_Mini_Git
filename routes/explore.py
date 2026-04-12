from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from pages import explore_html

router = APIRouter()


@router.get("/explore", response_class=HTMLResponse)
async def explore_page():
    return explore_html
