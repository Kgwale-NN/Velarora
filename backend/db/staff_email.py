"""Email sign-in for staff; student identities remain Windows usernames."""
import re
import sqlite3

from backend.db._core import _conn
from backend.db.user_queries import _USER_SELECT, check_credentials


def normalize_email(value: str) -> str:
    email = value.strip().lower()
    if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)+", email, re.ASCII) or not email.isascii():
        raise ValueError("Enter a valid email address.")
    return email


def authenticate_login(identifier: str, password: str):
    row = _conn().execute(
        _USER_SELECT + "WHERE u.email = ? COLLATE NOCASE", (identifier.strip(),)
    ).fetchone()
    user = check_credentials(dict(row) if row else None, password)
    return user if user and user["role"] in ("admin", "teacher") else None


def link_account_email(user_id: int, value: str) -> None:
    email = normalize_email(value)
    try:
        with _conn() as conn:
            result = conn.execute(
                "UPDATE user SET email=? WHERE id=? AND email IS NULL",
                (email, user_id),
            )
            if result.rowcount != 1:
                raise ValueError("This account cannot set up an email.")
    except sqlite3.IntegrityError as exc:
        raise ValueError("This email is already in use.") from exc
