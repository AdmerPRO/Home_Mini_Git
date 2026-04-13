from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from core import app_paths
from core.auth import get_current_username
from core.database import User, get_db
from core.logger import get_logger
from core.security import hash_identifier
from utils.repository_manager_util import (
    create_repository,
    get_repository_details,
    setup_start,
)

router = APIRouter()
logger = get_logger(__name__)


class CreateRepositoryRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")
    description: str = Field("", max_length=400)
    visibility: str = Field(..., pattern=r"^(public|private)$")
    project_names: list[str]

    @field_validator("project_names")
    @classmethod
    def validate_project_names(cls, value: list[str]) -> list[str]:
        normalized = []
        seen = set()

        for item in value:
            project_name = str(item).strip()
            if not project_name:
                continue
            if project_name in seen:
                continue
            seen.add(project_name)
            normalized.append(project_name)

        if not normalized:
            raise ValueError("At least one project is required")

        return normalized


@router.post("/repositories")
async def create_repository_endpoint(
    request: Request, req: CreateRepositoryRequest, db: Session = Depends(get_db)
):
    username = get_current_username(request)
    if not username:
        raise HTTPException(status_code=401, detail="Authentication required")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    setup_start(app_paths.DATA_ROOT)

    try:
        create_repository(
            app_paths.DATA_ROOT,
            username,
            req.name,
            private=req.visibility == "private",
            description=req.description,
            project_names=req.project_names,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    repository = get_repository_details(
        app_paths.DATA_ROOT,
        username,
        req.name,
        public_only=False,
        increment_views=False,
    )
    logger.info(
        "Repository created owner_hash=%s repository=%s",
        hash_identifier(username),
        req.name,
    )
    return {"success": True, "repository": repository}


@router.get("/repositories/{owner}/{repository_name}")
async def get_repository_endpoint(
    owner: str,
    repository_name: str,
    request: Request,
):
    current_username = get_current_username(request)
    can_view_private = current_username == owner

    repository = get_repository_details(
        app_paths.DATA_ROOT,
        owner,
        repository_name,
        public_only=not can_view_private,
        increment_views=True,
    )
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    return {
        "repository": repository,
        "viewer_is_owner": can_view_private,
    }
