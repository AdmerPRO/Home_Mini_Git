import html

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from core import app_paths
from core.auth import get_current_username
from core.database import User, get_db
from core.logger import get_logger
from core.rate_limit import limiter
from core.security import hash_identifier
from utils.repository_manager_util import (
    get_user_profile,
    get_user_repositories,
    setup_start,
    update_user_profile,
)

router = APIRouter()
logger = get_logger(__name__)


class UpdateProfileRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=50)
    bio: str = Field("", max_length=300)
    avatar_image: str = Field("", max_length=50_000)

    @field_validator("display_name", "bio")
    @classmethod
    def sanitize_text(cls, value: str) -> str:
        return html.escape(value.strip(), quote=False)

    @field_validator("avatar_image")
    @classmethod
    def validate_avatar_image(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            return ""
        allowed_prefixes = (
            "data:image/png;base64,",
            "data:image/jpeg;base64,",
            "data:image/jpg;base64,",
            "data:image/webp;base64,",
            "data:image/gif;base64,",
        )
        if not normalized.startswith(allowed_prefixes):
            raise ValueError("Avatar must be a base64 data image")
        return normalized


@router.patch("/profile")
@limiter.limit("10/minute")
async def patch_profile(
    request: Request, req: UpdateProfileRequest, db: Session = Depends(get_db)
):
    username = get_current_username(request, db)
    if not username:
        raise HTTPException(status_code=401, detail="Authentication required")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    setup_start(app_paths.DATA_ROOT)
    profile = update_user_profile(
        app_paths.DATA_ROOT,
        username,
        display_name=req.display_name,
        bio=req.bio,
        avatar_image=req.avatar_image,
    )
    logger.info("Profile updated for user_hash=%s", hash_identifier(username))
    return {"success": True, "profile": profile}


@router.get("/users/{username}")
async def get_public_user(username: str):
    setup_start(app_paths.DATA_ROOT)
    profile = get_user_profile(app_paths.DATA_ROOT, username)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    public_repositories = get_user_repositories(
        app_paths.DATA_ROOT, username, public_only=True
    )
    return {"profile": profile, "repositories": public_repositories}
