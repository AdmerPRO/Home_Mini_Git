import mimetypes
import difflib
import io
import json
import time
import zipfile
from pathlib import Path, PurePosixPath

from utils.repository_manager_util import touch_repository

LANGUAGE_BY_EXTENSION = {
    ".py": "Python",
    ".css": "CSS",
    ".html": "HTML",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".jsx": "JavaScript",
    ".json": "JSON",
    ".md": "Markdown",
    ".txt": "Text",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".toml": "TOML",
    ".sh": "Shell",
    ".bat": "Batch",
    ".ps1": "PowerShell",
    ".sql": "SQL",
}
SAFE_PATH_SEGMENT = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
)


def _project_root(
    base_path: Path, owner: str, repository_name: str, project_name: str
) -> Path:
    return (
        Path(base_path)
        / "user_projects"
        / owner
        / repository_name
        / "projects"
        / project_name
    )


def _history_root(base_path: Path, owner: str, repository_name: str) -> Path:
    return Path(base_path) / "user_projects" / owner / repository_name / "history"


def _repository_projects_root(
    base_path: Path, owner: str, repository_name: str
) -> Path:
    return Path(base_path) / "user_projects" / owner / repository_name / "projects"


def _write_history_entry(
    base_path: Path, owner: str, repository_name: str, entry: dict
) -> None:
    history_root = _history_root(base_path, owner, repository_name)
    history_root.mkdir(parents=True, exist_ok=True)
    timestamp = int(time.time() * 1000)
    entry_path = (
        history_root / f"{timestamp}_{entry['project_name'].replace('/', '_')}.json"
    )
    entry_path.write_text(
        json.dumps(entry, indent=4, ensure_ascii=False), encoding="utf-8"
    )


def _normalize_relative_path(relative_path: str) -> str:
    normalized = str(relative_path).replace("\\", "/").strip().strip("/")
    if not normalized:
        raise ValueError("File path is required")

    pure = PurePosixPath(normalized)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError("Invalid file path")

    for part in pure.parts:
        if not part or any(char not in SAFE_PATH_SEGMENT for char in part):
            raise ValueError("Invalid file path")

    return pure.as_posix()


def _resolve_project_file(
    base_path: Path,
    owner: str,
    repository_name: str,
    project_name: str,
    relative_path: str,
) -> tuple[Path, str]:
    project_root = _project_root(base_path, owner, repository_name, project_name)
    if not project_root.exists():
        raise ValueError("Project not found")

    normalized_path = _normalize_relative_path(relative_path)
    full_path = project_root / normalized_path
    try:
        full_path.resolve().relative_to(project_root.resolve())
    except ValueError as exc:
        raise ValueError("Invalid file path") from exc

    return full_path, normalized_path


def list_project_files(
    base_path: Path, owner: str, repository_name: str, project_name: str
) -> list[dict]:
    project_root = _project_root(base_path, owner, repository_name, project_name)
    if not project_root.exists():
        raise ValueError("Project not found")

    files = []
    for file_path in sorted(project_root.rglob("*")):
        if not file_path.is_file():
            continue
        relative = file_path.relative_to(project_root).as_posix()
        files.append(
            {
                "path": relative,
                "size": file_path.stat().st_size,
                "updated_at": int(file_path.stat().st_mtime * 1000),
                "mime_type": mimetypes.guess_type(file_path.name)[0] or "text/plain",
                "is_readme": relative.lower() == "readme.md",
            }
        )

    return files


def read_project_file(
    base_path: Path,
    owner: str,
    repository_name: str,
    project_name: str,
    relative_path: str,
) -> dict:
    file_path, normalized_path = _resolve_project_file(
        base_path, owner, repository_name, project_name, relative_path
    )
    if not file_path.exists() or not file_path.is_file():
        raise ValueError("File not found")

    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Only UTF-8 text files are supported") from exc

    return {
        "path": normalized_path,
        "content": content,
        "size": file_path.stat().st_size,
        "updated_at": int(file_path.stat().st_mtime * 1000),
        "mime_type": mimetypes.guess_type(file_path.name)[0] or "text/plain",
    }


def project_file_exists(
    base_path: Path,
    owner: str,
    repository_name: str,
    project_name: str,
    relative_path: str,
) -> bool:
    file_path, _ = _resolve_project_file(
        base_path, owner, repository_name, project_name, relative_path
    )
    return file_path.exists() and file_path.is_file()


def write_project_file(
    base_path: Path,
    owner: str,
    repository_name: str,
    project_name: str,
    relative_path: str,
    content: str,
) -> dict:
    file_path, normalized_path = _resolve_project_file(
        base_path, owner, repository_name, project_name, relative_path
    )
    old_content = None
    action = "created"
    if file_path.exists():
        action = "updated"
        try:
            old_content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            old_content = None

    new_content = str(content)
    if old_content is not None and old_content == new_content:
        return read_project_file(
            base_path, owner, repository_name, project_name, normalized_path
        )

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(new_content, encoding="utf-8")
    touch_repository(base_path, owner, repository_name)
    diff_text = ""
    if old_content is None:
        diff_text = "".join(
            difflib.unified_diff(
                [],
                new_content.splitlines(keepends=True),
                fromfile=f"a/{normalized_path}",
                tofile=f"b/{normalized_path}",
            )
        )
    else:
        diff_text = "".join(
            difflib.unified_diff(
                old_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=f"a/{normalized_path}",
                tofile=f"b/{normalized_path}",
            )
        )
    _write_history_entry(
        base_path,
        owner,
        repository_name,
        {
            "project_name": project_name,
            "path": normalized_path,
            "action": action,
            "changed_at": int(time.time() * 1000),
            "diff": diff_text,
        },
    )
    return read_project_file(
        base_path, owner, repository_name, project_name, normalized_path
    )


def write_project_bytes(
    base_path: Path,
    owner: str,
    repository_name: str,
    project_name: str,
    relative_path: str,
    content: bytes,
) -> dict:
    file_path, normalized_path = _resolve_project_file(
        base_path, owner, repository_name, project_name, relative_path
    )
    old_bytes = file_path.read_bytes() if file_path.exists() else b""
    if old_bytes == content:
        return {
            "path": normalized_path,
            "size": len(content),
            "updated_at": (
                int(file_path.stat().st_mtime * 1000)
                if file_path.exists()
                else int(time.time() * 1000)
            ),
        }

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(content)
    touch_repository(base_path, owner, repository_name)
    _write_history_entry(
        base_path,
        owner,
        repository_name,
        {
            "project_name": project_name,
            "path": normalized_path,
            "action": "uploaded",
            "changed_at": int(time.time() * 1000),
            "diff": {
                "old_size": len(old_bytes),
                "new_size": len(content),
                "binary": True,
            },
        },
    )
    return {
        "path": normalized_path,
        "size": len(content),
        "updated_at": int(file_path.stat().st_mtime * 1000),
    }


def upload_project_files(
    base_path: Path,
    owner: str,
    repository_name: str,
    project_name: str,
    files: list[tuple[str, bytes]],
) -> list[dict]:
    uploaded = []
    for relative_path, content in files:
        uploaded.append(
            write_project_bytes(
                base_path,
                owner,
                repository_name,
                project_name,
                relative_path,
                content,
            )
        )
    return uploaded


def get_repository_language_stats(
    base_path: Path, owner: str, repository_name: str
) -> dict:
    repository_projects_root = _repository_projects_root(
        base_path, owner, repository_name
    )
    if not repository_projects_root.exists():
        raise ValueError("Repository not found")

    totals: dict[str, int] = {}
    total_bytes = 0
    for file_path in repository_projects_root.rglob("*"):
        if not file_path.is_file():
            continue
        file_size = file_path.stat().st_size
        if file_size <= 0:
            continue
        language = LANGUAGE_BY_EXTENSION.get(file_path.suffix.lower(), "Other")
        totals[language] = totals.get(language, 0) + file_size
        total_bytes += file_size

    languages = []
    if total_bytes > 0:
        for language, bytes_count in sorted(
            totals.items(), key=lambda item: (-item[1], item[0].lower())
        ):
            languages.append(
                {
                    "language": language,
                    "bytes": bytes_count,
                    "percent": round((bytes_count / total_bytes) * 100, 1),
                }
            )

    return {
        "total_bytes": total_bytes,
        "languages": languages,
    }


def build_repository_zip(
    base_path: Path, owner: str, repository_name: str
) -> io.BytesIO:
    repository_projects_root = _repository_projects_root(
        base_path, owner, repository_name
    )
    if not repository_projects_root.exists():
        raise ValueError("Repository not found")

    archive = io.BytesIO()
    archive_root = f"{repository_name}/"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in sorted(repository_projects_root.rglob("*")):
            if not file_path.is_file():
                continue
            relative_path = file_path.relative_to(repository_projects_root).as_posix()
            zip_file.write(file_path, arcname=f"{archive_root}{relative_path}")

    archive.seek(0)
    return archive
