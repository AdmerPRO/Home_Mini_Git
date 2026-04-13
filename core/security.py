import hashlib
import os
import threading
import time

LOGIN_FAILURE_LIMIT = int(os.getenv("LOGIN_FAILURE_LIMIT", "10"))
LOGIN_LOCKOUT_SECONDS = int(os.getenv("LOGIN_LOCKOUT_SECONDS", "900"))

_login_failure_lock = threading.Lock()
_failed_login_attempts: dict[str, list[float]] = {}
_locked_accounts: dict[str, float] = {}


def hash_identifier(value: str) -> str:
    normalized = value.strip().lower().encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()[:8]


def _normalize_username(username: str) -> str:
    return username.strip().lower()


def _prune_state(username: str, now: float) -> None:
    attempts = _failed_login_attempts.get(username, [])
    if attempts:
        window_start = now - LOGIN_LOCKOUT_SECONDS
        attempts = [attempt for attempt in attempts if attempt >= window_start]
        if attempts:
            _failed_login_attempts[username] = attempts
        else:
            _failed_login_attempts.pop(username, None)

    locked_until = _locked_accounts.get(username)
    if locked_until is not None and locked_until <= now:
        _locked_accounts.pop(username, None)


def is_account_locked(username: str) -> bool:
    normalized = _normalize_username(username)
    now = time.time()
    with _login_failure_lock:
        _prune_state(normalized, now)
        locked_until = _locked_accounts.get(normalized)
        return locked_until is not None and locked_until > now


def register_failed_login(username: str) -> bool:
    normalized = _normalize_username(username)
    now = time.time()
    with _login_failure_lock:
        _prune_state(normalized, now)
        attempts = _failed_login_attempts.setdefault(normalized, [])
        attempts.append(now)
        if len(attempts) >= LOGIN_FAILURE_LIMIT:
            _locked_accounts[normalized] = now + LOGIN_LOCKOUT_SECONDS
            _failed_login_attempts.pop(normalized, None)
            return True
        return False


def clear_failed_logins(username: str) -> None:
    normalized = _normalize_username(username)
    with _login_failure_lock:
        _failed_login_attempts.pop(normalized, None)
        _locked_accounts.pop(normalized, None)


def reset_login_protection_state() -> None:
    with _login_failure_lock:
        _failed_login_attempts.clear()
        _locked_accounts.clear()
