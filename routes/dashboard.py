from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from core.auth import get_current_username, redirect_to_login
from core.database import User, get_db
from pages import dashboard_html

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, db: Session = Depends(get_db)):
    username = get_current_username(request)
    if not username:
        return redirect_to_login()

    user = db.query(User).filter(User.username == username).first()
    if not user:
        return redirect_to_login()

    response = HTMLResponse(content=dashboard_html)
    response.headers["Cache-Control"] = "no-store"
    return response
