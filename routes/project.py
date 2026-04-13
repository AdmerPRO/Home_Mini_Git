import os

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PROJECT_HTML_PATH = os.path.join(BASE_DIR, "sites", "project", "index.html")

router = APIRouter()


def _read_project_html() -> str:
    with open(PROJECT_HTML_PATH, "r", encoding="utf-8") as file:
        return file.read()


@router.get("/repositories/{owner}/{repository_name}", response_class=HTMLResponse)
async def repository_page(owner: str, repository_name: str):
    return HTMLResponse(content=_read_project_html())
