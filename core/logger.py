import gzip
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from core.app_paths import SERVER_ROOT

load_dotenv()

LOGS_DIR = SERVER_ROOT / "logs"
LATEST_LOG_PATH = LOGS_DIR / "latest.txt"
_FILE_HANDLER_NAME = "home-mini-git-latest-file"


def _is_debug_enabled() -> bool:
    return os.getenv("DEBUG", "false").strip().lower() in {"1", "true", "yes", "on"}


def _build_archive_path(source_path: Path) -> Path:
    created_at = datetime.fromtimestamp(source_path.stat().st_ctime)
    base_name = created_at.strftime("%Y-%m-%d_%H-%M-%S")
    archive_path = LOGS_DIR / f"{base_name}.txt.gz"
    suffix = 1

    while archive_path.exists():
        archive_path = LOGS_DIR / f"{base_name}_{suffix}.txt.gz"
        suffix += 1

    return archive_path


def _archive_previous_latest_log() -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    if not LATEST_LOG_PATH.exists():
        return

    archive_path = _build_archive_path(LATEST_LOG_PATH)
    with LATEST_LOG_PATH.open("rb") as source_file, gzip.open(
        archive_path, "wb"
    ) as archive_file:
        shutil.copyfileobj(source_file, archive_file)

    # Reset latest.txt in place so the next FileHandler writes from a clean file
    # without relying on rename/delete semantics that can be flaky on Windows.
    LATEST_LOG_PATH.write_text("", encoding="utf-8")


def _ensure_file_handler(
    root_logger: logging.Logger, formatter: logging.Formatter, level: int
) -> None:
    for handler in root_logger.handlers:
        if getattr(handler, "name", "") == _FILE_HANDLER_NAME:
            handler.setLevel(level)
            handler.setFormatter(formatter)
            return

    file_handler = logging.FileHandler(LATEST_LOG_PATH, encoding="utf-8")
    file_handler.set_name(_FILE_HANDLER_NAME)
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)


def _remove_non_file_handlers(root_logger: logging.Logger) -> None:
    for handler in list(root_logger.handlers):
        if getattr(handler, "name", "") == _FILE_HANDLER_NAME:
            continue
        root_logger.removeHandler(handler)
        handler.close()


def configure_logging() -> None:
    level = logging.DEBUG if _is_debug_enabled() else logging.INFO
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    root_logger = logging.getLogger()
    has_file_handler = any(
        getattr(handler, "name", "") == _FILE_HANDLER_NAME
        for handler in root_logger.handlers
    )

    if not has_file_handler:
        _archive_previous_latest_log()

    root_logger.setLevel(level)
    _ensure_file_handler(root_logger, formatter, level)
    _remove_non_file_handlers(root_logger)

    for handler in root_logger.handlers:
        handler.setLevel(level)

    for logger_name in (
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "watchfiles",
        "watchfiles.main",
    ):
        app_logger = logging.getLogger(logger_name)
        app_logger.handlers.clear()
        app_logger.propagate = True
        if logger_name.startswith("watchfiles"):
            app_logger.setLevel(logging.WARNING)
        else:
            app_logger.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
