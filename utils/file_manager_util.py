import json
from pathlib import Path


def _projects_root(base_path: Path) -> Path:
    return Path(base_path) / "user_projects"


def _index_file(base_path: Path) -> Path:
    return _projects_root(base_path) / "projects_index.json"


def _load_project_index(base_path: Path) -> dict:
    index_file = _index_file(base_path)
    if not index_file.exists():
        return {"users": {}, "projects": {}, "project_names": {}}

    with open(index_file, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_project_index(base_path: Path, data: dict) -> None:
    index_file = _index_file(base_path)
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def _ensure_user_in_index(base_path: Path, username: str) -> None:
    data = _load_project_index(base_path)
    data["users"].setdefault(username, [])
    _save_project_index(base_path, data)


def _register_project_in_index(
    base_path: Path, username: str, project_name: str
) -> None:
    data = _load_project_index(base_path)
    user_projects = data["users"].setdefault(username, [])
    if project_name not in user_projects:
        user_projects.append(project_name)
        user_projects.sort()

    project_key = f"{username}/{project_name}"
    data["projects"][project_key] = {
        "owner": username,
        "project_name": project_name,
        "path": project_key,
    }

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
        _save_project_index(
            base_path, {"users": {}, "projects": {}, "project_names": {}}
        )
    return True


def _extract_username(user_or_username) -> str:
    # Accept either a raw username string or an object with a username attribute.
    username = getattr(user_or_username, "username", user_or_username)
    return str(username)


def add_user(base_path: Path, username):
    username = _extract_username(username)
    Path(f"{base_path}/user_projects/{username}").mkdir(parents=True, exist_ok=True)
    Path(f"{base_path}/user_tests/runner/{username}").mkdir(parents=True, exist_ok=True)
    Path(f"{base_path}/deployed_projects/{username}").mkdir(parents=True, exist_ok=True)
    _ensure_user_in_index(base_path, username)
    return True


def create_project(base_path: Path, username, name, private):
    path = Path(f"{base_path}/user_projects") / username / name
    path.mkdir(parents=True, exist_ok=True)

    settings_file = path / "settings.txt"
    settings = {
        "owner": username,
        "project_name": name,
        "private": private,
        "contributors": [username],
        "description": "HomeMiniGit Project!",
    }
    settings_file.write_text(json.dumps(settings, indent=4))

    Path(f"{path}/issues").mkdir(parents=True, exist_ok=True)
    Path(f"{path}/files").mkdir(parents=True, exist_ok=True)
    Path(f"{path}/history").mkdir(parents=True, exist_ok=True)
    _register_project_in_index(base_path, username, name)
    return True


def add_contributor(base_path: Path, username, project, owner):
    path = Path(f"{base_path}/user_projects") / owner / project
    settings_file = path / "settings.txt"
    with open(settings_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["contributors"].append(username)
    with open(settings_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    return True


def get_user_projects(base_path: Path, username: str) -> list[str]:
    data = _load_project_index(base_path)
    return data["users"].get(username, [])


def get_project_owner(
    base_path: Path, project_name: str, owner: str | None = None
) -> str | list[str] | None:
    data = _load_project_index(base_path)

    if owner is not None:
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
