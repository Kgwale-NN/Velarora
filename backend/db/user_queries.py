"""User queries operations."""
from __future__ import annotations
from typing import Optional
from backend.db._core import _conn
from backend.db.user_passwords import _DUMMY_HASH
from backend.db.user_passwords import _verify_pw


_USER_SELECT = """
    SELECT u.id, u.username, u.email, u.hashed_password,
           u.role_id, r.name AS role,
           u.is_active, u.created_by, u.created_at
    FROM   user u
    JOIN   role r ON r.id = u.role_id
"""


def list_roles() -> list[dict]:
    c = _conn()
    return [dict(r) for r in c.execute("SELECT * FROM role ORDER BY id").fetchall()]


def get_role_id(name: str) -> Optional[int]:
    c = _conn()
    row = c.execute("SELECT id FROM role WHERE name = ?", (name,)).fetchone()
    return int(row["id"]) if row else None


def get_user_by_username(username: str) -> Optional[dict]:
    c = _conn()
    row = c.execute(_USER_SELECT + "WHERE u.username = ?", (username,)).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[dict]:
    c = _conn()
    row = c.execute(_USER_SELECT + "WHERE u.id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def verify_password(username: str, password: str) -> Optional[dict]:
    """
    Timing-safe credential check: the bcrypt comparison always runs — against
    the real hash when the user exists (active or not), against _DUMMY_HASH
    otherwise — so response time never reveals whether a username is valid.
    """
    user = get_user_by_username(username)
    return check_credentials(user, password)


def check_credentials(user: Optional[dict], password: str) -> Optional[dict]:
    hashed = user["hashed_password"] if user else _DUMMY_HASH
    ok = _verify_pw(password, hashed)
    if ok and user and user.get("is_active"):
        return user
    return None


def list_users() -> list[dict]:
    c = _conn()
    return [dict(r) for r in c.execute(
        _USER_SELECT + "ORDER BY r.name, u.username"
    ).fetchall()]
