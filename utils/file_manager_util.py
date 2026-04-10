import json
from pathlib import Path


def setup_start(base_path: Path):
    Path(f"{base_path}/user_projects").mkdir(parents=True, exist_ok=True)
    Path(f"{base_path}/user_tests/runner").mkdir(parents=True, exist_ok=True)
    Path(f"{base_path}/deployed_projects").mkdir(parents=True, exist_ok=True)
    return True


def add_user(base_path: Path, username):
    Path(f"{base_path}/user_projects/{username}").mkdir(parents=True, exist_ok=True)
    Path(f"{base_path}/user_tests/runner/{username}").mkdir(parents=True, exist_ok=True)
    Path(f"{base_path}/deployed_projects/{username}").mkdir(parents=True, exist_ok=True)
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
    return True


if __name__ == "__main__":
    setup_start(Path("../"))
    add_user(Path("../"), "AdmerPRO")
    create_project(Path("../"), "AdmerPRO", "HomeMiniGit", False)
