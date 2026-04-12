from pathlib import Path


def _find_server_root() -> Path:
    """Walk up from this file until we find the directory that contains
    pytest.ini (the project root).  That directory is the 'server' root
    regardless of what the containing folder happens to be named on disk."""
    candidate = Path(__file__).resolve().parent
    while candidate != candidate.parent:
        if (candidate / "pytest.ini").exists():
            return candidate
        candidate = candidate.parent
    # Fallback: two levels up from this file (original behaviour)
    return Path(__file__).resolve().parent.parent


SERVER_ROOT = _find_server_root()
DATA_ROOT = SERVER_ROOT
