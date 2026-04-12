from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from pages import user_profile_html

router = APIRouter()


@router.get("/users/{username}", response_class=HTMLResponse)
async def user_profile_page(username: str):
    return user_profile_html
