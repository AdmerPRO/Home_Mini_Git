import json
import re
import time
from pathlib import Path

DEFAULT_USER_BIO = "This builder has not added a bio yet."
DEFAULT_REPOSITORY_DESCRIPTION = "No repository description added yet."
DEFAULT_PROJECT_DESCRIPTION = "No project description added yet."
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,50}$")
REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,50}$")
PROJECT_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,50}$")
INDEX_FILENAME = "repositories_index.json"
LEGACY_INDEX_FILENAME = "projects_index.json"


def _now_ms() -> int:
    return int(time.time() * 1000)


def _empty_index() -> dict:
    return {"users": {}, "repositories": {}, "repository_names": {}, "profiles": {}}


def _normalize_index(data: dict | None) -> dict:
    normalized = _empty_index()
    if not isinstance(data, dict):
        return normalized

    for key in normalized:
        value = data.get(key)
        normalized[key] = value if isinstance(value, dict) else {}

    return normalized


def _projects_root(base_path: Path) -> Path:
    return Path(base_path) / "user_projects"


def _index_file(base_path: Path) -> Path:
    return _projects_root(base_path) / INDEX_FILENAME


def _legacy_index_file(base_path: Path) -> Path:
    return _projects_root(base_path) / LEGACY_INDEX_FILENAME


def _repository_root(base_path: Path, username: str, repository_name: str) -> Path:
    return _projects_root(base_path) / username / repository_name


def _settings_file(base_path: Path, username: str, repository_name: str) -> Path:
    return _repository_root(base_path, username, repository_name) / "settings.txt"


def _repository_projects_root(
    base_path: Path, username: str, repository_name: str
) -> Path:
    return _repository_root(base_path, username, repository_name) / "projects"


def _repository_project_dir(
    base_path: Path, username: str, repository_name: str, project_name: str
) -> Path:
    return (
        _repository_projects_root(base_path, username, repository_name) / project_name
    )


def _load_index(base_path: Path) -> dict:
    index_file = _index_file(base_path)
    legacy_index_file = _legacy_index_file(base_path)
    if not index_file.exists():
        if not legacy_index_file.exists():
            return _empty_index()

        with open(legacy_index_file, "r", encoding="utf-8") as f:
            legacy_data = json.load(f)

        normalized = _empty_index()
        if isinstance(legacy_data.get("users"), dict):
            normalized["users"] = legacy_data["users"]
        if isinstance(legacy_data.get("profiles"), dict):
            normalized["profiles"] = legacy_data["profiles"]
        if isinstance(legacy_data.get("projects"), dict):
            for key, metadata in legacy_data["projects"].items():
                if not isinstance(metadata, dict):
                    continue
                owner = metadata.get("owner")
                project_name = metadata.get("project_name")
                if not owner or not project_name:
                    continue
                normalized["repositories"][key] = {
                    "owner": owner,
                    "repository_name": project_name,
                    "path": metadata.get("path", key),
                    "private": metadata.get("private", True),
                    "description": metadata.get(
                        "description", DEFAULT_REPOSITORY_DESCRIPTION
                    ),
                    "contributors": metadata.get("contributors", [owner]),
                    "contributors_count": metadata.get("contributors_count", 1),
                    "created_at": metadata.get("created_at", _now_ms()),
                    "updated_at": metadata.get("updated_at", _now_ms()),
                    "views": metadata.get("views", 0),
                    "projects": [
                        {"name": "main", "description": DEFAULT_PROJECT_DESCRIPTION}
                    ],
                    "project_names": ["main"],
                    "projects_count": 1,
                }
        if isinstance(legacy_data.get("project_names"), dict):
            normalized["repository_names"] = legacy_data["project_names"]
        return normalized

    with open(index_file, "r", encoding="utf-8") as f:
        return _normalize_index(json.load(f))


def _save_index(base_path: Path, data: dict) -> None:
    _projects_root(base_path).mkdir(parents=True, exist_ok=True)
    with open(_index_file(base_path), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def _extract_username(user_or_username) -> str:
    username = getattr(user_or_username, "username", user_or_username)
    return str(username).strip()


def _is_safe_username(username: str) -> bool:
    return bool(USERNAME_PATTERN.fullmatch(username))


def _is_safe_repository_name(repository_name: str) -> bool:
    return bool(REPOSITORY_PATTERN.fullmatch(repository_name))


def _is_safe_project_name(project_name: str) -> bool:
    return bool(PROJECT_PATTERN.fullmatch(project_name))


def _require_safe_username(user_or_username) -> str:
    username = _extract_username(user_or_username)
    if not _is_safe_username(username):
        raise ValueError("Invalid username")
    return username


def _require_safe_repository_name(repository_name) -> str:
    normalized_name = str(repository_name).strip()
    if not _is_safe_repository_name(normalized_name):
        raise ValueError("Invalid repository name")
    return normalized_name


def _require_safe_project_name(project_name) -> str:
    normalized_name = str(project_name).strip()
    if not _is_safe_project_name(normalized_name):
        raise ValueError("Invalid project name")
    return normalized_name


def _default_profile(username: str, joined_at: int | None = None) -> dict:
    return {
        "username": username,
        "display_name": username,
        "bio": DEFAULT_USER_BIO,
        "avatar_image": "",
        "joined_at": joined_at if joined_at is not None else _now_ms(),
    }


def _default_project_entry(project_name: str) -> dict:
    return {
        "name": project_name,
        "description": f"Workspace module for {project_name}.",
    }


def _normalize_project_entries(project_names: list[str]) -> list[dict]:
    normalized_projects = []
    seen = set()

    for raw_name in project_names:
        project_name = _require_safe_project_name(raw_name)
        if project_name in seen:
            continue
        normalized_projects.append(_default_project_entry(project_name))
        seen.add(project_name)

    if not normalized_projects:
        raise ValueError("At least one project is required")

    return normalized_projects


def _read_repository_settings(
    base_path: Path, username: str, repository_name: str
) -> dict | None:
    settings_file = _settings_file(base_path, username, repository_name)
    if not settings_file.exists():
        return None

    with open(settings_file, "r", encoding="utf-8") as f:
        settings = json.load(f)

    if "repository_name" not in settings:
        settings = {
            "owner": username,
            "repository_name": repository_name,
            "private": bool(settings.get("private", True)),
            "contributors": settings.get("contributors", [username]),
            "pending_invites": settings.get("pending_invites", []),
            "description": str(
                settings.get("description", DEFAULT_REPOSITORY_DESCRIPTION)
            ).strip()
            or DEFAULT_REPOSITORY_DESCRIPTION,
            "projects": [{"name": "main", "description": DEFAULT_PROJECT_DESCRIPTION}],
            "views": int(settings.get("views", 0)),
            "created_at": int(settings.get("created_at", _now_ms())),
            "updated_at": int(settings.get("updated_at", _now_ms())),
        }
        _write_repository_structure(base_path, username, repository_name, settings)

    return settings


def _write_repository_settings(
    base_path: Path, username: str, repository_name: str, settings: dict
) -> None:
    with open(
        _settings_file(base_path, username, repository_name), "w", encoding="utf-8"
    ) as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)


def _repository_readme_body(
    repository_name: str, description: str, projects: list[dict]
) -> str:
    lines = [f"# {repository_name}", "", description, "", "## Projects", ""]
    for project in projects:
        lines.append(f"- {project['name']}: {project['description']}")
    lines.append("")
    return "\n".join(lines)


def _write_repository_structure(
    base_path: Path, username: str, repository_name: str, settings: dict
) -> None:
    repository_path = _repository_root(base_path, username, repository_name)
    repository_path.mkdir(parents=True, exist_ok=True)
    (repository_path / "issues").mkdir(parents=True, exist_ok=True)
    (repository_path / "history").mkdir(parents=True, exist_ok=True)
    _repository_projects_root(base_path, username, repository_name).mkdir(
        parents=True, exist_ok=True
    )

    for project in settings["projects"]:
        project_dir = _repository_project_dir(
            base_path, username, repository_name, project["name"]
        )
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "README.md").write_text(
            f"# {repository_name}/{project['name']}\n\n{project['description']}\n",
            encoding="utf-8",
        )

    (repository_path / "README.md").write_text(
        _repository_readme_body(
            repository_name, settings["description"], settings["projects"]
        ),
        encoding="utf-8",
    )
    _write_repository_settings(base_path, username, repository_name, settings)


def setup_start(base_path: Path):
    Path(f"{base_path}/user_projects").mkdir(parents=True, exist_ok=True)
    Path(f"{base_path}/user_tests/runner").mkdir(parents=True, exist_ok=True)
    Path(f"{base_path}/deployed_projects").mkdir(parents=True, exist_ok=True)
    _save_index(base_path, _load_index(base_path))
    return True


def _repository_metadata(
    base_path: Path, username: str, repository_name: str
) -> dict | None:
    settings = _read_repository_settings(base_path, username, repository_name)
    if not settings:
        return None

    contributors = settings.get("contributors", [])
    projects = settings.get("projects", [])
    return {
        "owner": username,
        "repository_name": repository_name,
        "path": f"{username}/{repository_name}",
        "private": bool(settings.get("private", True)),
        "description": str(settings.get("description", DEFAULT_REPOSITORY_DESCRIPTION)),
        "contributors": contributors,
        "contributors_count": len(contributors),
        "pending_invites": list(settings.get("pending_invites", [])),
        "created_at": int(settings.get("created_at", _now_ms())),
        "updated_at": int(settings.get("updated_at", _now_ms())),
        "views": int(settings.get("views", 0)),
        "projects": projects,
        "project_names": [project["name"] for project in projects],
        "projects_count": len(projects),
    }


def _register_repository_in_index(
    base_path: Path, username: str, repository_name: str
) -> None:
    data = _load_index(base_path)
    user_repositories = data["users"].setdefault(username, [])
    if repository_name not in user_repositories:
        user_repositories.append(repository_name)
        user_repositories.sort()

    repository_key = f"{username}/{repository_name}"
    metadata = _repository_metadata(base_path, username, repository_name)
    if metadata:
        data["repositories"][repository_key] = metadata

    owners = data["repository_names"].setdefault(repository_name, [])
    if username not in owners:
        owners.append(username)
        owners.sort()

    _save_index(base_path, data)


def _ensure_user_in_index(base_path: Path, username: str) -> None:
    data = _load_index(base_path)
    data["users"].setdefault(username, [])
    _save_index(base_path, data)


def _ensure_user_profile(
    base_path: Path, username: str, joined_at: int | None = None
) -> None:
    data = _load_index(base_path)
    profile = data["profiles"].get(username)
    if not isinstance(profile, dict):
        data["profiles"][username] = _default_profile(username, joined_at=joined_at)
    else:
        profile.setdefault("username", username)
        profile.setdefault("display_name", username)
        profile.setdefault("bio", DEFAULT_USER_BIO)
        profile.setdefault("avatar_image", "")
        profile.setdefault(
            "joined_at", joined_at if joined_at is not None else _now_ms()
        )
        data["profiles"][username] = profile

    _save_index(base_path, data)


def add_user(base_path: Path, username, joined_at: int | None = None):
    username = _require_safe_username(username)
    Path(f"{base_path}/user_projects/{username}").mkdir(parents=True, exist_ok=True)
    Path(f"{base_path}/user_tests/runner/{username}").mkdir(parents=True, exist_ok=True)
    Path(f"{base_path}/deployed_projects/{username}").mkdir(parents=True, exist_ok=True)
    _ensure_user_in_index(base_path, username)
    _ensure_user_profile(base_path, username, joined_at=joined_at)
    return True


def create_repository(
    base_path: Path,
    username,
    name,
    private,
    description: str | None = None,
    project_names: list[str] | None = None,
):
    username = _require_safe_username(username)
    repository_name = _require_safe_repository_name(name)
    repository_path = _repository_root(base_path, username, repository_name)
    if repository_path.exists():
        raise ValueError("Repository already exists")

    normalized_projects = _normalize_project_entries(project_names or [])
    now_ms = _now_ms()
    settings = {
        "owner": username,
        "repository_name": repository_name,
        "private": private,
        "contributors": [username],
        "pending_invites": [],
        "description": (description or DEFAULT_REPOSITORY_DESCRIPTION).strip()
        or DEFAULT_REPOSITORY_DESCRIPTION,
        "projects": normalized_projects,
        "views": 0,
        "created_at": now_ms,
        "updated_at": now_ms,
    }
    _write_repository_structure(base_path, username, repository_name, settings)
    _register_repository_in_index(base_path, username, repository_name)
    return True


def add_repository_project(
    base_path: Path,
    username,
    repository_name,
    project_name,
    description: str | None = None,
):
    username = _require_safe_username(username)
    repository_name = _require_safe_repository_name(repository_name)
    project_name = _require_safe_project_name(project_name)

    settings = _read_repository_settings(base_path, username, repository_name)
    if not settings:
        raise ValueError("Repository not found")

    if any(project["name"] == project_name for project in settings["projects"]):
        raise ValueError("Project already exists in repository")

    settings["projects"].append(
        {
            "name": project_name,
            "description": (description or DEFAULT_PROJECT_DESCRIPTION).strip()
            or DEFAULT_PROJECT_DESCRIPTION,
        }
    )
    settings["updated_at"] = _now_ms()
    _write_repository_structure(base_path, username, repository_name, settings)
    _register_repository_in_index(base_path, username, repository_name)
    return True


def add_contributor(base_path: Path, username, repository_name, owner):
    username = _require_safe_username(username)
    owner = _require_safe_username(owner)
    repository_name = _require_safe_repository_name(repository_name)
    settings = _read_repository_settings(base_path, owner, repository_name)
    if not settings:
        raise ValueError("Repository not found")

    contributors = settings.setdefault("contributors", [])
    if username not in contributors:
        contributors.append(username)
    invites = settings.setdefault("pending_invites", [])
    if username in invites:
        invites.remove(username)
    settings["updated_at"] = _now_ms()
    _write_repository_settings(base_path, owner, repository_name, settings)
    _register_repository_in_index(base_path, owner, repository_name)
    return True


def is_repository_contributor(
    base_path: Path, username: str, repository_name: str, owner: str
) -> bool:
    if not _is_safe_username(str(username).strip()):
        return False
    settings = _read_repository_settings(base_path, owner, repository_name)
    if not settings:
        return False
    contributors = settings.get("contributors", [])
    return username == owner or username in contributors


def invite_contributor(
    base_path: Path, owner: str, repository_name: str, username: str
):
    owner = _require_safe_username(owner)
    username = _require_safe_username(username)
    repository_name = _require_safe_repository_name(repository_name)
    settings = _read_repository_settings(base_path, owner, repository_name)
    if not settings:
        raise ValueError("Repository not found")

    contributors = settings.setdefault("contributors", [owner])
    if username in contributors:
        raise ValueError("User is already a contributor")

    invites = settings.setdefault("pending_invites", [])
    if username in invites:
        raise ValueError("Invitation already exists")

    invites.append(username)
    settings["updated_at"] = _now_ms()
    _write_repository_settings(base_path, owner, repository_name, settings)
    _register_repository_in_index(base_path, owner, repository_name)
    return True


def accept_contributor_invite(
    base_path: Path, username: str, owner: str, repository_name: str
) -> bool:
    owner = _require_safe_username(owner)
    username = _require_safe_username(username)
    repository_name = _require_safe_repository_name(repository_name)
    settings = _read_repository_settings(base_path, owner, repository_name)
    if not settings:
        raise ValueError("Repository not found")

    invites = settings.setdefault("pending_invites", [])
    if username not in invites:
        raise ValueError("Invitation not found")

    invites.remove(username)
    contributors = settings.setdefault("contributors", [owner])
    if username not in contributors:
        contributors.append(username)
    settings["updated_at"] = _now_ms()
    _write_repository_settings(base_path, owner, repository_name, settings)
    _register_repository_in_index(base_path, owner, repository_name)
    return True


def get_pending_repository_invites(base_path: Path, username: str) -> list[dict]:
    username = _require_safe_username(username)
    data = _load_index(base_path)
    invites = []

    for repository_key, metadata in data["repositories"].items():
        if not isinstance(metadata, dict):
            continue
        owner = metadata.get("owner")
        repository_name = metadata.get("repository_name")
        if not owner or not repository_name:
            continue

        settings = _read_repository_settings(base_path, owner, repository_name)
        if not settings:
            continue
        if username not in settings.get("pending_invites", []):
            continue

        invites.append(
            {
                "owner": owner,
                "repository_name": repository_name,
                "description": str(
                    settings.get("description", DEFAULT_REPOSITORY_DESCRIPTION)
                ),
                "created_at": int(settings.get("created_at", _now_ms())),
            }
        )

    invites.sort(
        key=lambda item: (-item["created_at"], item["repository_name"].lower())
    )
    return invites


def get_user_repository_names(base_path: Path, username: str) -> list[str]:
    if not _is_safe_username(str(username).strip()):
        return []
    data = _load_index(base_path)
    return data["users"].get(username, [])


def get_user_repositories(
    base_path: Path, username: str, public_only: bool = False
) -> list[dict]:
    repositories = []
    for repository_name in get_user_repository_names(base_path, username):
        metadata = _repository_metadata(base_path, username, repository_name)
        if not metadata:
            continue
        if public_only and metadata["private"]:
            continue
        repositories.append(metadata)

    return sorted(
        repositories,
        key=lambda item: (-item["updated_at"], item["repository_name"].lower()),
    )


def get_accessible_repositories(base_path: Path, username: str) -> list[dict]:
    if not _is_safe_username(str(username).strip()):
        return []

    data = _load_index(base_path)
    repositories = []
    seen = set()
    for repository_key, metadata in data["repositories"].items():
        if not isinstance(metadata, dict):
            continue
        owner = metadata.get("owner")
        repository_name = metadata.get("repository_name")
        if not owner or not repository_name:
            continue

        current_metadata = _repository_metadata(base_path, owner, repository_name)
        if not current_metadata:
            continue
        if username != owner and username not in current_metadata.get(
            "contributors", []
        ):
            continue
        key = (owner, repository_name)
        if key in seen:
            continue
        seen.add(key)
        repositories.append(current_metadata)

    return sorted(
        repositories,
        key=lambda item: (-item["updated_at"], item["repository_name"].lower()),
    )


def get_repository_details(
    base_path: Path,
    owner: str,
    repository_name: str,
    public_only: bool = False,
    increment_views: bool = False,
) -> dict | None:
    if not _is_safe_username(str(owner).strip()):
        return None
    if not _is_safe_repository_name(str(repository_name).strip()):
        return None

    settings = _read_repository_settings(base_path, owner, repository_name)
    if not settings:
        return None

    if public_only and bool(settings.get("private", True)):
        return None

    if increment_views:
        settings["views"] = int(settings.get("views", 0)) + 1
        _write_repository_settings(base_path, owner, repository_name, settings)
        _register_repository_in_index(base_path, owner, repository_name)

    return _repository_metadata(base_path, owner, repository_name)


def get_public_repositories(base_path: Path, limit: int | None = None) -> list[dict]:
    data = _load_index(base_path)
    repositories = []

    for repository_key, metadata in data["repositories"].items():
        if not isinstance(metadata, dict):
            continue

        owner = metadata.get("owner")
        repository_name = metadata.get("repository_name")
        if not owner or not repository_name:
            continue

        current_metadata = _repository_metadata(base_path, owner, repository_name)
        if not current_metadata or current_metadata["private"]:
            continue

        repositories.append(current_metadata)

    repositories.sort(
        key=lambda item: (
            -item["views"],
            -item["updated_at"],
            item["repository_name"].lower(),
        )
    )
    return repositories[:limit] if limit is not None else repositories


def get_user_profile(base_path: Path, username: str) -> dict | None:
    if not _is_safe_username(str(username).strip()):
        return None

    data = _load_index(base_path)
    profile = data["profiles"].get(username)
    if not isinstance(profile, dict):
        return None

    public_repositories = get_user_repositories(base_path, username, public_only=True)
    return {
        "username": username,
        "display_name": str(profile.get("display_name", username)),
        "bio": str(profile.get("bio", DEFAULT_USER_BIO)),
        "avatar_image": str(profile.get("avatar_image", "")),
        "joined_at": int(profile.get("joined_at", _now_ms())),
        "public_repository_count": len(public_repositories),
        "public_project_total": sum(
            repository["projects_count"] for repository in public_repositories
        ),
        "total_views": sum(repository["views"] for repository in public_repositories),
    }


def update_user_profile(
    base_path: Path,
    username: str,
    display_name: str | None = None,
    bio: str | None = None,
    avatar_image: str | None = None,
) -> dict:
    username = _require_safe_username(username)
    data = _load_index(base_path)
    current = data["profiles"].get(username)
    if not isinstance(current, dict):
        current = _default_profile(username)

    if display_name is not None:
        current["display_name"] = display_name.strip() or username
    if bio is not None:
        current["bio"] = bio.strip() or DEFAULT_USER_BIO
    if avatar_image is not None:
        current["avatar_image"] = avatar_image.strip()

    current.setdefault("joined_at", _now_ms())
    data["profiles"][username] = current
    _save_index(base_path, data)
    profile = get_user_profile(base_path, username)
    if profile is None:
        raise ValueError("Profile could not be updated")
    return profile


def touch_repository(base_path: Path, username: str, repository_name: str) -> bool:
    username = _require_safe_username(username)
    repository_name = _require_safe_repository_name(repository_name)
    settings = _read_repository_settings(base_path, username, repository_name)
    if not settings:
        raise ValueError("Repository not found")

    settings["updated_at"] = _now_ms()
    _write_repository_settings(base_path, username, repository_name, settings)
    _register_repository_in_index(base_path, username, repository_name)
    return True


def get_public_user_cards(
    base_path: Path, exclude_username: str | None = None, limit: int | None = None
) -> list[dict]:
    data = _load_index(base_path)
    users = []
    for username in sorted(data["profiles"]):
        if exclude_username and username == exclude_username:
            continue
        profile = get_user_profile(base_path, username)
        if not profile:
            continue
        users.append(profile)

    users.sort(
        key=lambda item: (
            -item["public_repository_count"],
            -item["total_views"],
            item["display_name"].lower(),
        )
    )
    return users[:limit] if limit is not None else users


def get_repository_owner(
    base_path: Path, repository_name: str, owner: str | None = None
) -> str | list[str] | None:
    if not _is_safe_repository_name(str(repository_name).strip()):
        return None
    data = _load_index(base_path)

    if owner is not None:
        if not _is_safe_username(str(owner).strip()):
            return None
        repository_key = f"{owner}/{repository_name}"
        repository_data = data["repositories"].get(repository_key)
        return repository_data["owner"] if repository_data else None

    owners = data["repository_names"].get(repository_name, [])
    if not owners:
        return None
    if len(owners) == 1:
        return owners[0]
    return owners
