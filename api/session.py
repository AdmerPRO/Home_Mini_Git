from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from core import app_paths
from core.auth import (
    SESSION_COOKIE_NAME,
    clear_session_cookie,
    decrypt_token,
    get_current_username,
    revoke_access_token,
)
from core.database import User, get_db
from utils.repository_manager_util import (
    get_accessible_repositories,
    get_user_profile,
)

router = APIRouter()


@router.get("/session")
async def get_session(
    request: Request, response: Response, db: Session = Depends(get_db)
):
    username = get_current_username(request, db)
    if not username:
        clear_session_cookie(response)
        response.headers["Cache-Control"] = "no-store"
        return {"authenticated": False}

    user = db.query(User).filter(User.username == username).first()
    if not user:
        clear_session_cookie(response)
        response.headers["Cache-Control"] = "no-store"
        return {"authenticated": False}

    repository_cards = get_accessible_repositories(app_paths.DATA_ROOT, username)
    profile = get_user_profile(app_paths.DATA_ROOT, username)
    response.headers["Cache-Control"] = "no-store"
    return {
        "authenticated": True,
        "nickname": username,
        "repositories": sorted(item["repository_name"] for item in repository_cards),
        "repository_cards": repository_cards,
        "profile": profile,
    }


@router.post("/logout")
async def logout(
    request: Request, response: Response, db: Session = Depends(get_db)
):
    encrypted_token = request.cookies.get(SESSION_COOKIE_NAME)
    if encrypted_token:
        token = decrypt_token(encrypted_token)
        if token:
            revoke_access_token(token, db)
    clear_session_cookie(response)
    response.headers["Cache-Control"] = "no-store"
    return {"success": True}
