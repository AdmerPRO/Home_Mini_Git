from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from pages import project_html

router = APIRouter()


@router.get("/repositories/{owner}/{repository_name}", response_class=HTMLResponse)
async def repository_page(owner: str, repository_name: str):
    return project_html
