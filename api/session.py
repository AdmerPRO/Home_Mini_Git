from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from core import app_paths
from core.auth import clear_session_cookie, get_current_username
from core.database import User, get_db
from utils.repository_manager_util import (
    get_user_profile,
    get_user_repositories,
    get_user_repository_names,
)

router = APIRouter()


@router.get("/session")
async def get_session(
    request: Request, response: Response, db: Session = Depends(get_db)
):
    username = get_current_username(request)
    if not username:
        clear_session_cookie(response)
        response.headers["Cache-Control"] = "no-store"
        return {"authenticated": False}

    user = db.query(User).filter(User.username == username).first()
    if not user:
        clear_session_cookie(response)
        response.headers["Cache-Control"] = "no-store"
        return {"authenticated": False}

    repository_cards = get_user_repositories(app_paths.DATA_ROOT, username)
    profile = get_user_profile(app_paths.DATA_ROOT, username)
    response.headers["Cache-Control"] = "no-store"
    return {
        "authenticated": True,
        "nickname": username,
        "repositories": get_user_repository_names(app_paths.DATA_ROOT, username),
        "repository_cards": repository_cards,
        "profile": profile,
    }


@router.post("/logout")
async def logout(response: Response):
    clear_session_cookie(response)
    response.headers["Cache-Control"] = "no-store"
    return {"success": True}
