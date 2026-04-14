import hashlib
import os
import threading
import time

LOGIN_FAILURE_LIMIT = int(os.getenv("LOGIN_FAILURE_LIMIT", "10"))
LOGIN_LOCKOUT_SECONDS = int(os.getenv("LOGIN_LOCKOUT_SECONDS", "900"))

_login_failure_lock = threading.Lock()
_failed_login_attempts: dict[str, list[float]] = {}
_locked_accounts: dict[str, float] = {}
_ip_failed_login_attempts: dict[str, list[float]] = {}
_locked_ips: dict[str, float] = {}


def hash_identifier(value: str) -> str:
    normalized = value.strip().lower().encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()[:8]


def _normalize_username(username: str) -> str:
    return username.strip().lower()


def _normalize_ip(ip: str) -> str:
    return ip.strip().lower()


def _prune_attempt_window(attempts_by_key: dict[str, list[float]], key: str, now: float) -> None:
    attempts = attempts_by_key.get(key, [])
    if attempts:
        window_start = now - LOGIN_LOCKOUT_SECONDS
        attempts = [attempt for attempt in attempts if attempt >= window_start]
        if attempts:
            attempts_by_key[key] = attempts
        else:
            attempts_by_key.pop(key, None)


def _prune_lock(lock_by_key: dict[str, float], key: str, now: float) -> None:
    locked_until = lock_by_key.get(key)
    if locked_until is not None and locked_until <= now:
        lock_by_key.pop(key, None)


def _prune_state(username: str, ip: str, now: float) -> None:
    _prune_attempt_window(_failed_login_attempts, username, now)
    _prune_lock(_locked_accounts, username, now)
    if ip:
        _prune_attempt_window(_ip_failed_login_attempts, ip, now)
        _prune_lock(_locked_ips, ip, now)


def is_account_locked(username: str, ip: str = "") -> bool:
    normalized = _normalize_username(username)
    normalized_ip = _normalize_ip(ip)
    now = time.time()
    with _login_failure_lock:
        _prune_state(normalized, normalized_ip, now)
        locked_until = _locked_accounts.get(normalized)
        if locked_until is not None and locked_until > now:
            return True
        if not normalized_ip:
            return False
        ip_locked_until = _locked_ips.get(normalized_ip)
        return ip_locked_until is not None and ip_locked_until > now


def register_failed_login(username: str, ip: str = "") -> bool:
    normalized = _normalize_username(username)
    normalized_ip = _normalize_ip(ip)
    now = time.time()
    with _login_failure_lock:
        _prune_state(normalized, normalized_ip, now)
        attempts = _failed_login_attempts.setdefault(normalized, [])
        attempts.append(now)
        username_locked = len(attempts) >= LOGIN_FAILURE_LIMIT
        if username_locked:
            _locked_accounts[normalized] = now + LOGIN_LOCKOUT_SECONDS
            _failed_login_attempts.pop(normalized, None)
        ip_locked = False
        if normalized_ip:
            ip_attempts = _ip_failed_login_attempts.setdefault(normalized_ip, [])
            ip_attempts.append(now)
            ip_locked = len(ip_attempts) >= LOGIN_FAILURE_LIMIT
            if ip_locked:
                _locked_ips[normalized_ip] = now + LOGIN_LOCKOUT_SECONDS
                _ip_failed_login_attempts.pop(normalized_ip, None)
        return username_locked or ip_locked


def clear_failed_logins(username: str, ip: str = "") -> None:
    normalized = _normalize_username(username)
    normalized_ip = _normalize_ip(ip)
    with _login_failure_lock:
        _failed_login_attempts.pop(normalized, None)
        _locked_accounts.pop(normalized, None)
        if normalized_ip:
            _ip_failed_login_attempts.pop(normalized_ip, None)
            _locked_ips.pop(normalized_ip, None)


def reset_login_protection_state() -> None:
    with _login_failure_lock:
        _failed_login_attempts.clear()
        _locked_accounts.clear()
        _ip_failed_login_attempts.clear()
        _locked_ips.clear()
