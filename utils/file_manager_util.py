import json
import re
import time
from pathlib import Path

DEFAULT_USER_BIO = "This builder has not added a bio yet."
DEFAULT_PROJECT_DESCRIPTION = "No description added yet."
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,50}$")
PROJECT_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,50}$")


def _now_ms() -> int:
    return int(time.time() * 1000)


def _empty_index() -> dict:
    return {"users": {}, "projects": {}, "project_names": {}, "profiles": {}}


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
    return _projects_root(base_path) / "projects_index.json"


def _project_root(base_path: Path, username: str, project_name: str) -> Path:
    return _projects_root(base_path) / username / project_name


def _settings_file(base_path: Path, username: str, project_name: str) -> Path:
    return _project_root(base_path, username, project_name) / "settings.txt"


def _load_project_index(base_path: Path) -> dict:
    index_file = _index_file(base_path)
    if not index_file.exists():
        return _empty_index()

    with open(index_file, "r", encoding="utf-8") as f:
        return _normalize_index(json.load(f))


def _save_project_index(base_path: Path, data: dict) -> None:
    _projects_root(base_path).mkdir(parents=True, exist_ok=True)
    index_file = _index_file(base_path)
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def _default_profile(username: str, joined_at: int | None = None) -> dict:
    return {
        "username": username,
        "display_name": username,
        "bio": DEFAULT_USER_BIO,
        "joined_at": joined_at if joined_at is not None else _now_ms(),
    }


def _ensure_user_in_index(base_path: Path, username: str) -> None:
    data = _load_project_index(base_path)
    data["users"].setdefault(username, [])
    _save_project_index(base_path, data)


def _ensure_user_profile(
    base_path: Path, username: str, joined_at: int | None = None
) -> None:
    data = _load_project_index(base_path)
    profile = data["profiles"].get(username)
    if not isinstance(profile, dict):
        data["profiles"][username] = _default_profile(username, joined_at=joined_at)
    else:
        profile.setdefault("username", username)
        profile.setdefault("display_name", username)
        profile.setdefault("bio", DEFAULT_USER_BIO)
        profile.setdefault(
            "joined_at", joined_at if joined_at is not None else _now_ms()
        )
        data["profiles"][username] = profile

    _save_project_index(base_path, data)


def _read_project_settings(
    base_path: Path, username: str, project_name: str
) -> dict | None:
    settings_file = _settings_file(base_path, username, project_name)
    if not settings_file.exists():
        return None

    with open(settings_file, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_project_settings(
    base_path: Path, username: str, project_name: str, settings: dict
) -> None:
    settings_file = _settings_file(base_path, username, project_name)
    with open(settings_file, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)


def _project_metadata(base_path: Path, username: str, project_name: str) -> dict | None:
    settings = _read_project_settings(base_path, username, project_name)
    if not settings:
        return None

    contributors = settings.get("contributors", [])
    return {
        "owner": username,
        "project_name": project_name,
        "path": f"{username}/{project_name}",
        "private": bool(settings.get("private", True)),
        "description": str(settings.get("description", DEFAULT_PROJECT_DESCRIPTION)),
        "contributors": contributors,
        "contributors_count": len(contributors),
        "created_at": int(settings.get("created_at", _now_ms())),
        "updated_at": int(settings.get("updated_at", _now_ms())),
        "views": int(settings.get("views", 0)),
    }


def _register_project_in_index(
    base_path: Path, username: str, project_name: str
) -> None:
    data = _load_project_index(base_path)
    user_projects = data["users"].setdefault(username, [])
    if project_name not in user_projects:
        user_projects.append(project_name)
        user_projects.sort()

    project_key = f"{username}/{project_name}"
    metadata = _project_metadata(base_path, username, project_name)
    if metadata:
        data["projects"][project_key] = metadata

    owners = data["project_names"].setdefault(project_name, [])
    if username not in owners:
        owners.append(username)
        owners.sort()

    _save_project_index(base_path, data)


def setup_start(base_path: Path):
    Path(f"{base_path}/user_projects").mkdir(parents=True, exist_ok=True)
    Path(f"{base_path}/user_tests/runner").mkdir(parents=True, exist_ok=True)
    Path(f"{base_path}/deployed_projects").mkdir(parents=True, exist_ok=True)
    if not _index_file(base_path).exists():
        _save_project_index(base_path, _empty_index())
    else:
        _save_project_index(base_path, _load_project_index(base_path))
    return True


def _extract_username(user_or_username) -> str:
    # Accept either a raw username string or an object with a username attribute.
    username = getattr(user_or_username, "username", user_or_username)
    return str(username).strip()


def _is_safe_username(username: str) -> bool:
    return bool(USERNAME_PATTERN.fullmatch(username))


def _is_safe_project_name(project_name: str) -> bool:
    return bool(PROJECT_PATTERN.fullmatch(project_name))


def _require_safe_username(user_or_username) -> str:
    username = _extract_username(user_or_username)
    if not _is_safe_username(username):
        raise ValueError("Invalid username")
    return username


def _require_safe_project_name(project_name) -> str:
    normalized_name = str(project_name).strip()
    if not _is_safe_project_name(normalized_name):
        raise ValueError("Invalid project name")
    return normalized_name


def add_user(base_path: Path, username, joined_at: int | None = None):
    username = _require_safe_username(username)
    Path(f"{base_path}/user_projects/{username}").mkdir(parents=True, exist_ok=True)
    Path(f"{base_path}/user_tests/runner/{username}").mkdir(parents=True, exist_ok=True)
    Path(f"{base_path}/deployed_projects/{username}").mkdir(parents=True, exist_ok=True)
    _ensure_user_in_index(base_path, username)
    _ensure_user_profile(base_path, username, joined_at=joined_at)
    return True


def create_project(
    base_path: Path,
    username,
    name,
    private,
    description: str | None = None,
):
    username = _require_safe_username(username)
    name = _require_safe_project_name(name)
    path = Path(f"{base_path}/user_projects") / username / name
    if path.exists():
        raise ValueError("Project already exists")

    path.mkdir(parents=True, exist_ok=True)
    now_ms = _now_ms()

    settings_file = path / "settings.txt"
    settings = {
        "owner": username,
        "project_name": name,
        "private": private,
        "contributors": [username],
        "description": (description or DEFAULT_PROJECT_DESCRIPTION).strip()
        or DEFAULT_PROJECT_DESCRIPTION,
        "views": 0,
        "created_at": now_ms,
        "updated_at": now_ms,
    }
    settings_file.write_text(json.dumps(settings, indent=4, ensure_ascii=False))

    Path(f"{path}/issues").mkdir(parents=True, exist_ok=True)
    Path(f"{path}/files").mkdir(parents=True, exist_ok=True)
    Path(f"{path}/history").mkdir(parents=True, exist_ok=True)
    (path / "files" / "README.md").write_text(
        f"# {name}\n\n{settings['description']}\n", encoding="utf-8"
    )
    _register_project_in_index(base_path, username, name)
    return True


def add_contributor(base_path: Path, username, project, owner):
    username = _require_safe_username(username)
    owner = _require_safe_username(owner)
    project = _require_safe_project_name(project)
    path = Path(f"{base_path}/user_projects") / owner / project
    settings_file = path / "settings.txt"
    with open(settings_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    contributors = data.setdefault("contributors", [])
    if username not in contributors:
        contributors.append(username)
    data["updated_at"] = _now_ms()
    with open(settings_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    _register_project_in_index(base_path, owner, project)
    return True


def get_user_projects(base_path: Path, username: str) -> list[str]:
    if not _is_safe_username(str(username).strip()):
        return []
    data = _load_project_index(base_path)
    return data["users"].get(username, [])


def get_user_project_cards(
    base_path: Path, username: str, public_only: bool = False
) -> list[dict]:
    if not _is_safe_username(str(username).strip()):
        return []
    data = _load_project_index(base_path)
    projects = []
    for project_name in data["users"].get(username, []):
        metadata = _project_metadata(base_path, username, project_name)
        if not metadata:
            continue
        if public_only and metadata["private"]:
            continue
        projects.append(metadata)

    return sorted(
        projects,
        key=lambda item: (-item["updated_at"], item["project_name"].lower()),
    )


def get_project_details(
    base_path: Path,
    owner: str,
    project_name: str,
    public_only: bool = False,
    increment_views: bool = False,
) -> dict | None:
    if not _is_safe_username(str(owner).strip()):
        return None
    if not _is_safe_project_name(str(project_name).strip()):
        return None
    settings = _read_project_settings(base_path, owner, project_name)
    if not settings:
        return None

    if public_only and bool(settings.get("private", True)):
        return None

    if increment_views:
        settings["views"] = int(settings.get("views", 0)) + 1
        _write_project_settings(base_path, owner, project_name, settings)
        _register_project_in_index(base_path, owner, project_name)

    return _project_metadata(base_path, owner, project_name)


def get_public_projects(base_path: Path, limit: int | None = None) -> list[dict]:
    data = _load_project_index(base_path)
    projects = []

    for project_key, metadata in data["projects"].items():
        if not isinstance(metadata, dict):
            continue

        owner = metadata.get("owner")
        project_name = metadata.get("project_name")
        if not owner or not project_name:
            continue

        current_metadata = _project_metadata(base_path, owner, project_name)
        if not current_metadata or current_metadata["private"]:
            continue

        projects.append(current_metadata)

    projects.sort(
        key=lambda item: (
            -item["views"],
            -item["updated_at"],
            item["project_name"].lower(),
        )
    )
    return projects[:limit] if limit is not None else projects


def get_user_profile(base_path: Path, username: str) -> dict | None:
    if not _is_safe_username(str(username).strip()):
        return None
    data = _load_project_index(base_path)
    profile = data["profiles"].get(username)
    if not isinstance(profile, dict):
        return None

    public_projects = get_user_project_cards(base_path, username, public_only=True)
    return {
        "username": username,
        "display_name": str(profile.get("display_name", username)),
        "bio": str(profile.get("bio", DEFAULT_USER_BIO)),
        "joined_at": int(profile.get("joined_at", _now_ms())),
        "public_project_count": len(public_projects),
        "total_views": sum(project["views"] for project in public_projects),
    }


def update_user_profile(
    base_path: Path,
    username: str,
    display_name: str | None = None,
    bio: str | None = None,
) -> dict:
    username = _require_safe_username(username)
    data = _load_project_index(base_path)
    current = data["profiles"].get(username)
    if not isinstance(current, dict):
        current = _default_profile(username)

    if display_name is not None:
        current["display_name"] = display_name.strip() or username
    if bio is not None:
        current["bio"] = bio.strip() or DEFAULT_USER_BIO

    current.setdefault("joined_at", _now_ms())
    data["profiles"][username] = current
    _save_project_index(base_path, data)
    profile = get_user_profile(base_path, username)
    if profile is None:
        raise ValueError("Profile could not be updated")
    return profile


def get_public_user_cards(
    base_path: Path, exclude_username: str | None = None, limit: int | None = None
) -> list[dict]:
    data = _load_project_index(base_path)
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
            -item["public_project_count"],
            -item["total_views"],
            item["display_name"].lower(),
        )
    )
    return users[:limit] if limit is not None else users


def get_project_owner(
    base_path: Path, project_name: str, owner: str | None = None
) -> str | list[str] | None:
    if not _is_safe_project_name(str(project_name).strip()):
        return None
    data = _load_project_index(base_path)

    if owner is not None:
        if not _is_safe_username(str(owner).strip()):
            return None
        project_key = f"{owner}/{project_name}"
        project_data = data["projects"].get(project_key)
        return project_data["owner"] if project_data else None

    owners = data["project_names"].get(project_name, [])
    if not owners:
        return None
    if len(owners) == 1:
        return owners[0]
    return owners


if __name__ == "__main__":
    setup_start(Path("../"))
    add_user(Path("../"), "AdmerPRO")
    create_project(Path("../"), "AdmerPRO", "HomeMiniGit", False)
