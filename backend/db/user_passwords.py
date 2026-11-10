"""User passwords operations."""
from __future__ import annotations
import bcrypt


def _min_password_length() -> int:
    """
    Minimum password length: PASSWORD_MIN_LENGTH in .env, default 8.
    Read directly from os.environ (config.py has loaded .env by the time
    this module is imported at runtime) so the db layer stays free of the
    nicegui import that backend.config drags in. Floor of 1 — the policy can be
    relaxed but never lets an empty password through. Invalid values fall
    back to the default. Changes require an app restart.
    """
    import os
    raw = os.environ.get("PASSWORD_MIN_LENGTH", "").strip()
    if not raw:
        return 8
    try:
        return max(1, int(raw))
    except ValueError:
        return 8


MIN_PASSWORD_LENGTH = _min_password_length()


def validate_password(password: str) -> None:
    """Raise ValueError when the password fails the policy."""
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
        )


def _hash_pw(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_pw(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


_DUMMY_HASH = _hash_pw("dummy-password-for-constant-time-compare")
