"""Session lifetime, roles and page access for Velarora."""
from __future__ import annotations
from typing import Optional
import time
from backend.core.session_cookie import REMEMBER_SECONDS
from nicegui import app as nicegui_app, ui


def get_session_user() -> Optional[dict]:
    deadline = nicegui_app.storage.user.get("remember_until")
    if deadline is not None and time.time() >= deadline:
        clear_session()
        return None
    user = nicegui_app.storage.user.get("auth")
    if user and user.get("role") not in ("admin", "teacher"):
        clear_session()
        return None
    return user


def set_session_user(user: dict, remember: bool = False) -> None:
    if user.get("role") not in ("admin", "teacher"):
        clear_session()
        raise ValueError("Only staff can sign in to Velarora.")
    nicegui_app.storage.user["remember_until"] = time.time() + REMEMBER_SECONDS if remember else None
    nicegui_app.storage.user["auth"] = {
        "id":       user["id"],
        "username": user["username"],
        "role":     user["role"],
    }


def clear_session() -> None:
    nicegui_app.storage.user.pop("auth", None)
    nicegui_app.storage.user.pop("remember_until", None)


def is_admin(user: dict) -> bool:
    return user.get("role") == "admin"


def is_teacher(user: dict) -> bool:
    return user.get("role") == "teacher"


def is_teacher_or_admin(user: dict) -> bool:
    return user.get("role") in ("admin", "teacher")


def home_path_for(user: dict) -> str:
    """Landing page the given user is actually allowed to open."""
    role = user.get("role")
    if role == "admin":
        return "/users"
    if role == "teacher":
        return "/"
    return "/login"


def require_auth(required_role: Optional[str] = None) -> Optional[dict]:
    """
    Return current user or redirect.

    required_role=None       → any authenticated staff member
    required_role="admin"    → admin only
    required_role="teacher"  → teacher only  (NOT admin)
    required_role="teacher_or_admin" → teacher or admin

    When the role check fails, we redirect to the user's own home page
    (not a fixed "/") so the destination is always a page they can open.
    Student identities are monitoring records and never receive website access.
    """
    user = get_session_user()
    if not user:
        ui.navigate.to("/login")
        return None

    home = home_path_for(user)

    if required_role == "admin" and user["role"] != "admin":
        ui.navigate.to(home)
        return None

    if required_role == "teacher" and user["role"] != "teacher":
        ui.navigate.to(home)
        return None

    if required_role == "teacher_or_admin" and \
            user["role"] not in ("admin", "teacher"):
        ui.navigate.to(home)
        return None

    return user