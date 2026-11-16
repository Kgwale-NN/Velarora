"""User passwords operations."""
from __future__ import annotations
import bcrypt


def _min_password_length() -> int:
    """Allow installations to require more than twelve characters."""
    import os
    raw = os.environ.get("PASSWORD_MIN_LENGTH", "").strip()
    if not raw:
        return 12
    try:
        return max(12, int(raw))
    except ValueError:
        return 12


MIN_PASSWORD_LENGTH = _min_password_length()


def validate_password(password: str) -> None:
    """Raise ValueError when the password fails the policy."""
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
        )
    if not password[0].isupper():
        raise ValueError("Start with a capital letter.")
    if not any(char.isdecimal() for char in password):
        raise ValueError("Include a number.")
    if not any(not char.isalnum() and not char.isspace() and char.isprintable() for char in password):
        raise ValueError("Include a symbol, such as ! or #.")
    if len(password.encode()) > 72:
        raise ValueError("Use at most 72 bytes for your password.")


def _hash_pw(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_pw(password: str, hashed: str) -> bool:
    if len(password.encode()) > 72:
        return False
    return bcrypt.checkpw(password.encode(), hashed.encode())


_DUMMY_HASH = _hash_pw("dummy-password-for-constant-time-compare")
