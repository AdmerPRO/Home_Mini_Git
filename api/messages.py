import html

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from core import app_paths
from core.auth import get_current_username
from core.database import User, get_db
from core.logger import get_logger
from core.security import hash_identifier
from utils.message_manager_util import get_inbox, mark_message_read, send_message

router = APIRouter()
logger = get_logger(__name__)


class SendMessageRequest(BaseModel):
    recipient: str = Field(..., min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_]+$")
    subject: str = Field("", max_length=120)
    content: str = Field(..., min_length=1, max_length=5000)

    @field_validator("subject", "content")
    @classmethod
    def sanitize_text(cls, value: str) -> str:
        return html.escape(value.strip(), quote=False)


class MarkReadRequest(BaseModel):
    message_id: str = Field(..., min_length=1, max_length=64)


def _require_authenticated_user(request: Request, db: Session) -> str:
    username = get_current_username(request)
    if not username:
        raise HTTPException(status_code=401, detail="Authentication required")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return username


@router.get("/messages")
async def get_messages(request: Request, db: Session = Depends(get_db)):
    username = _require_authenticated_user(request, db)
    return {"messages": get_inbox(app_paths.DATA_ROOT, username)}


@router.post("/messages")
async def send_message_endpoint(
    request: Request, req: SendMessageRequest, db: Session = Depends(get_db)
):
    username = _require_authenticated_user(request, db)
    recipient = db.query(User).filter(User.username == req.recipient).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    if req.recipient == username:
        raise HTTPException(status_code=400, detail="You cannot message yourself")

    try:
        message = send_message(
            app_paths.DATA_ROOT,
            username,
            req.recipient,
            req.subject,
            req.content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    logger.info(
        "Message sent sender_hash=%s recipient_hash=%s",
        hash_identifier(username),
        hash_identifier(req.recipient),
    )
    return {"success": True, "message": message}


@router.post("/messages/read")
async def mark_message_read_endpoint(
    request: Request, req: MarkReadRequest, db: Session = Depends(get_db)
):
    username = _require_authenticated_user(request, db)
    updated = mark_message_read(app_paths.DATA_ROOT, username, req.message_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"success": True}
