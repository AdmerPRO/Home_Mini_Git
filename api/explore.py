from fastapi import APIRouter, Request

from core import app_paths
from core.auth import get_current_username
from core.logger import get_logger
from utils.repository_manager_util import (
    get_public_repositories,
    get_public_user_cards,
    setup_start,
)

router = APIRouter()
logger = get_logger(__name__)


@router.get("/explore")
async def get_explore(request: Request):
    setup_start(app_paths.DATA_ROOT)
    current_username = get_current_username(request)
    repositories = get_public_repositories(app_paths.DATA_ROOT, limit=8)
    users = get_public_user_cards(
        app_paths.DATA_ROOT, exclude_username=current_username, limit=8
    )
    logger.debug(
        "Explore feed loaded for viewer=%s repositories=%s users=%s",
        current_username or "anonymous",
        len(repositories),
        len(users),
    )
    return {"repositories": repositories, "users": users}
