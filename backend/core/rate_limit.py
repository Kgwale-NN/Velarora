"""Login protection: track both client IP and normalized username.

Either counter can block a login. A successful login clears both counters.
An attacker can temporarily lock a known username until its window expires.
"""
from backend.core.rate_limit_store import (
    MAX_ATTEMPTS, WINDOW_SEC, is_blocked, retry_after, record_failure,
    record_success, reset_all,
)

__all__ = [
    "MAX_ATTEMPTS", "WINDOW_SEC", "is_blocked", "retry_after", "record_failure",
    "record_success", "reset_all", "login_retry_after", "record_login_failure",
    "record_login_success",
]


def _login_keys(client_ip: str, username: str) -> list[str]:
    """
    Both tracking keys for one login attempt. The username key is normalized
    (stripped, lowercased, length-capped) so case variants of one account
    share a counter and absurdly long inputs can't bloat the dict.
    """
    keys = [f"ip:{client_ip}"]
    uname = (username or "").strip().lower()[:64]
    if uname:
        keys.append(f"user:{uname}")
    return keys


def login_retry_after(client_ip: str, username: str) -> float:
    """Seconds until this (IP, username) pair may try again — 0 if allowed."""
    return max(retry_after(k) for k in _login_keys(client_ip, username))


def record_login_failure(client_ip: str, username: str) -> None:
    for k in _login_keys(client_ip, username):
        record_failure(k)


def record_login_success(client_ip: str, username: str) -> None:
    for k in _login_keys(client_ip, username):
        record_success(k)
