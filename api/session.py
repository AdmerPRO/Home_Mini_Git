from pathlib import Path

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from auth import clear_session_cookie, get_current_username
from database import User, get_db
from utils.file_manager_util import get_user_projects

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

    projects = get_user_projects(Path("../"), username)
    response.headers["Cache-Control"] = "no-store"
    return {
        "authenticated": True,
        "nickname": username,
        "projects": projects,
    }


@router.post("/logout")
async def logout(response: Response):
    clear_session_cookie(response)
    response.headers["Cache-Control"] = "no-store"
    return {"success": True}
