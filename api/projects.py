from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from core import app_paths
from core.auth import get_current_username
from core.database import User, get_db
from core.logger import get_logger
from core.security import hash_identifier
from utils.repository_content_util import (
    build_repository_zip,
    get_repository_language_stats,
    list_project_files,
    project_file_exists,
    read_project_file,
    upload_project_files,
    write_project_file,
)
from utils.repository_manager_util import (
    accept_contributor_invite,
    add_repository_project,
    create_repository,
    get_repository_details,
    get_pending_repository_invites,
    invite_contributor,
    is_repository_contributor,
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


class CreateRepositoryProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")
    description: str = Field("", max_length=300)


class ProjectFileWriteRequest(BaseModel):
    path: str = Field(..., min_length=1, max_length=200)
    content: str = Field("", max_length=200_000)


class RepositoryInviteRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_]+$")


class AcceptInviteRequest(BaseModel):
    owner: str = Field(..., min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_]+$")
    repository_name: str = Field(
        ..., min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_-]+$"
    )


def _require_authenticated_user(request: Request, db: Session) -> str:
    username = get_current_username(request)
    if not username:
        raise HTTPException(status_code=401, detail="Authentication required")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    return username


def _require_repository_owner(
    request: Request, db: Session, owner: str, repository_name: str
) -> str:
    username = _require_authenticated_user(request, db)
    if username != owner:
        raise HTTPException(
            status_code=403, detail="Only the owner can perform this action"
        )

    repository = get_repository_details(
        app_paths.DATA_ROOT,
        owner,
        repository_name,
        public_only=False,
        increment_views=False,
    )
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    return username


def _can_view_repository(
    owner: str, repository_name: str, username: str | None
) -> bool:
    if username == owner:
        return True
    return is_repository_contributor(
        app_paths.DATA_ROOT, username or "", repository_name, owner
    )


def _require_repository_editor(
    request: Request, db: Session, owner: str, repository_name: str
) -> str:
    username = _require_authenticated_user(request, db)
    repository = get_repository_details(
        app_paths.DATA_ROOT,
        owner,
        repository_name,
        public_only=False,
        increment_views=False,
    )
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    if username != owner and username not in repository.get("contributors", []):
        raise HTTPException(
            status_code=403,
            detail="Only repository contributors can edit this repository",
        )
    return username


@router.post("/repositories")
async def create_repository_endpoint(
    request: Request, req: CreateRepositoryRequest, db: Session = Depends(get_db)
):
    username = _require_authenticated_user(request, db)
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
    can_view_private = _can_view_repository(owner, repository_name, current_username)

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
        "viewer_is_owner": current_username == owner,
        "viewer_can_edit": can_view_private,
    }


@router.post("/repositories/{owner}/{repository_name}/projects")
async def create_repository_project_endpoint(
    owner: str,
    repository_name: str,
    request: Request,
    req: CreateRepositoryProjectRequest,
    db: Session = Depends(get_db),
):
    _require_repository_owner(request, db, owner, repository_name)
    try:
        add_repository_project(
            app_paths.DATA_ROOT,
            owner,
            repository_name,
            req.name,
            description=req.description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    repository = get_repository_details(
        app_paths.DATA_ROOT,
        owner,
        repository_name,
        public_only=False,
        increment_views=False,
    )
    return {"success": True, "repository": repository}


@router.get("/repositories/{owner}/{repository_name}/languages")
async def get_repository_languages_endpoint(
    owner: str,
    repository_name: str,
    request: Request,
):
    current_username = get_current_username(request)
    can_view_private = _can_view_repository(owner, repository_name, current_username)
    repository = get_repository_details(
        app_paths.DATA_ROOT,
        owner,
        repository_name,
        public_only=not can_view_private,
        increment_views=False,
    )
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    try:
        stats = get_repository_language_stats(
            app_paths.DATA_ROOT, owner, repository_name
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return stats


@router.get("/repositories/{owner}/{repository_name}/archive.zip")
async def download_repository_archive_endpoint(
    owner: str,
    repository_name: str,
    request: Request,
):
    current_username = get_current_username(request)
    can_view_private = _can_view_repository(owner, repository_name, current_username)
    repository = get_repository_details(
        app_paths.DATA_ROOT,
        owner,
        repository_name,
        public_only=not can_view_private,
        increment_views=False,
    )
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    try:
        archive = build_repository_zip(app_paths.DATA_ROOT, owner, repository_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    filename = f"{repository_name}.zip"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(archive, media_type="application/zip", headers=headers)


@router.get("/repositories/{owner}/{repository_name}/projects/{project_name}/files")
async def list_project_files_endpoint(
    owner: str,
    repository_name: str,
    project_name: str,
    request: Request,
):
    current_username = get_current_username(request)
    can_view_private = _can_view_repository(owner, repository_name, current_username)
    repository = get_repository_details(
        app_paths.DATA_ROOT,
        owner,
        repository_name,
        public_only=not can_view_private,
        increment_views=False,
    )
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    try:
        files = list_project_files(
            app_paths.DATA_ROOT, owner, repository_name, project_name
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"files": files}


@router.get("/repositories/{owner}/{repository_name}/projects/{project_name}/file")
async def get_project_file_endpoint(
    owner: str,
    repository_name: str,
    project_name: str,
    request: Request,
    path: str = Query(..., min_length=1, max_length=200),
):
    current_username = get_current_username(request)
    can_view_private = _can_view_repository(owner, repository_name, current_username)
    repository = get_repository_details(
        app_paths.DATA_ROOT,
        owner,
        repository_name,
        public_only=not can_view_private,
        increment_views=False,
    )
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    try:
        file_data = read_project_file(
            app_paths.DATA_ROOT, owner, repository_name, project_name, path
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return file_data


@router.put("/repositories/{owner}/{repository_name}/projects/{project_name}/file")
async def update_project_file_endpoint(
    owner: str,
    repository_name: str,
    project_name: str,
    request: Request,
    req: ProjectFileWriteRequest,
    db: Session = Depends(get_db),
):
    username = _require_repository_editor(request, db, owner, repository_name)
    if username != owner and not project_file_exists(
        app_paths.DATA_ROOT,
        owner,
        repository_name,
        project_name,
        req.path,
    ):
        raise HTTPException(
            status_code=403,
            detail="Only the owner can add new files to this repository",
        )
    try:
        file_data = write_project_file(
            app_paths.DATA_ROOT,
            owner,
            repository_name,
            project_name,
            req.path,
            req.content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    logger.info(
        "Project file updated owner_hash=%s repository=%s project=%s path=%s",
        hash_identifier(owner),
        repository_name,
        project_name,
        req.path,
    )
    return {"success": True, "file": file_data}


@router.post("/repositories/{owner}/{repository_name}/invite")
async def invite_contributor_endpoint(
    owner: str,
    repository_name: str,
    request: Request,
    req: RepositoryInviteRequest,
    db: Session = Depends(get_db),
):
    inviter = _require_repository_owner(request, db, owner, repository_name)
    invited_user = db.query(User).filter(User.username == req.username).first()
    if not invited_user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        invite_contributor(app_paths.DATA_ROOT, owner, repository_name, req.username)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    logger.info(
        "Contributor invited owner_hash=%s invited_hash=%s repository=%s",
        hash_identifier(inviter),
        hash_identifier(req.username),
        repository_name,
    )
    return {"success": True}


@router.get("/repository-invitations")
async def get_repository_invitations_endpoint(
    request: Request, db: Session = Depends(get_db)
):
    username = _require_authenticated_user(request, db)
    return {
        "invitations": get_pending_repository_invites(app_paths.DATA_ROOT, username)
    }


@router.post("/repository-invitations/accept")
async def accept_repository_invitation_endpoint(
    request: Request,
    req: AcceptInviteRequest,
    db: Session = Depends(get_db),
):
    username = _require_authenticated_user(request, db)
    try:
        accept_contributor_invite(
            app_paths.DATA_ROOT,
            username,
            req.owner,
            req.repository_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True}


@router.post("/repositories/{owner}/{repository_name}/projects/{project_name}/upload")
async def upload_project_files_endpoint(
    owner: str,
    repository_name: str,
    project_name: str,
    request: Request,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    _require_repository_owner(request, db, owner, repository_name)
    prepared_files = []
    for file in files:
        if not file.filename:
            continue
        prepared_files.append((file.filename, await file.read()))

    if not prepared_files:
        raise HTTPException(status_code=400, detail="No files were uploaded")

    try:
        uploaded = upload_project_files(
            app_paths.DATA_ROOT,
            owner,
            repository_name,
            project_name,
            prepared_files,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    logger.info(
        "Project upload owner_hash=%s repository=%s project=%s files=%s",
        hash_identifier(owner),
        repository_name,
        project_name,
        len(uploaded),
    )
    return {"success": True, "files": uploaded}
