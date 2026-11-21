"""Shared staff authentication and CSRF dependencies for the React application."""

import secrets
from typing import Annotated
from fastapi import Depends, HTTPException, Header, Response
from backend.core.auth import get_session_user
from backend.db.user_queries import get_user_by_id
from backend.api.admin_security import browser_state


def staff(response: Response):
    response.headers["Cache-Control"] = "no-store"
    session = get_session_user()
    user = get_user_by_id(session["id"]) if session else None
    if not user or not user["is_active"] or user["role"] not in ("admin", "teacher"):
        raise HTTPException(401, "Sign in to continue.")
    return user


def teacher(actor: Annotated[dict, Depends(staff)]):
    if actor["role"] != "teacher":
        raise HTTPException(403, "Teacher access is required.")
    return actor


def check_csrf(token):
    expected = browser_state().get("admin_csrf", "")
    if not expected or not secrets.compare_digest(expected, token):
        raise HTTPException(403, "Refresh the page and try again.")


def write_staff(actor: Annotated[dict, Depends(staff)], x_csrf_token: str = Header(default="")):
    check_csrf(x_csrf_token)
    return actor


def write_teacher(actor: Annotated[dict, Depends(teacher)], x_csrf_token: str = Header(default="")):
    check_csrf(x_csrf_token)
    return actor
