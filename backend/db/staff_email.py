"""Email sign-in for staff; student identities remain Windows usernames."""
import re
import sqlite3

from backend.db._core import _conn
from backend.db.user_queries import _USER_SELECT, check_credentials, get_user_by_username


def normalize_email(value: str) -> str:
    email = value.strip().lower()
    if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)+", email, re.ASCII) or not email.isascii():
        raise ValueError("Enter a valid email address.")
    return email


def authenticate_login(identifier: str, password: str, mode: str):
    if mode == "staff":
        row = _conn().execute(
            _USER_SELECT + "WHERE u.email = ? COLLATE NOCASE AND r.name IN ('admin','teacher')",
            (identifier.strip(),),
        ).fetchone()
        user = dict(row) if row else None
    else:
        user = get_user_by_username(identifier)
        if user:
            student = mode == "student" and user["role"] == "student"
            setup = mode == "setup" and user["role"] in ("teacher", "admin") and not user["email"]
            if not (student or setup):
                user = None
    return check_credentials(user, password)


def link_staff_email(user_id: int, value: str) -> None:
    email = normalize_email(value)
    try:
        with _conn() as conn:
            result = conn.execute(
                "UPDATE user SET email=? WHERE id=? AND email IS NULL AND is_active=1 "
                "AND role_id IN (SELECT id FROM role WHERE name IN ('teacher','admin'))",
                (email, user_id),
            )
            if result.rowcount != 1:
                raise ValueError("This account cannot set up a staff email.")
    except sqlite3.IntegrityError as exc:
        raise ValueError("This email is already in use.") from exc
