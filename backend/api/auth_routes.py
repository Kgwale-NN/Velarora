"""React password sign-in and account self service; Google retains its OIDC backend."""

from typing import Annotated
from fastapi import APIRouter, Depends, Request, HTTPException, Response
from pydantic import BaseModel, Field, ConfigDict
from nicegui import run
from backend.api.admin_security import csrf_token, browser_state
from backend.api.staff_security import staff, write_staff, check_csrf
from backend.api.admin_routes import perform
from backend.core.auth import get_session_user, set_session_user, clear_session
from backend.core import rate_limit, google_login
from backend.db.staff_email import authenticate_login
from backend.db.user_queries import get_user_by_id, verify_password_by_id
from backend.db.user_updates import update_password

router = APIRouter(prefix="/api")


class Login(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=512)
    remember: bool = False


class Signup(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=128)
    confirm_password: str = Field(min_length=1, max_length=128)


def create_teacher_account(payload):
    from backend.db._core import _conn
    from backend.db.user_create import create_user
    from backend.db.staff_email import normalize_email

    name = payload.username.strip()
    if not name:
        raise ValueError("Enter your full name.")
    if payload.password != payload.confirm_password:
        raise ValueError("Your passwords do not match.")
    email = normalize_email(payload.email)
    with _conn():
        return create_user(name, payload.password, "teacher", email=email)


@router.post("/signup", status_code=201)
async def signup(payload: Signup, request: Request, response: Response):
    check_csrf(request.headers.get("X-CSRF-Token", ""))
    if get_session_user():
        raise HTTPException(409, "Log out before creating another account.")
    key = "signup:" + (request.client.host if request.client else "unknown")
    if rate_limit.retry_after(key) > 0:
        raise HTTPException(429, "Too many sign-up attempts. Please try again later.")
    rate_limit.record_failure(key)
    await perform(create_teacher_account, payload)
    response.headers["Cache-Control"] = "no-store"
    return {"ok": True, "message": "Your teacher account is ready. Sign in to continue."}


class Profile(BaseModel):
    username: str = Field(min_length=1, max_length=100)


class Password(BaseModel):
    current: str = Field(max_length=512)
    password: str = Field(min_length=12, max_length=128)


def public_user(user):
    return {k: user[k] for k in ("id", "username", "email", "role")} if user else None


@router.get("/session")
def session(request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    auth = get_session_user()
    user = get_user_by_id(auth["id"]) if auth else None
    if user and (not user["is_active"] or user["role"] not in ("admin", "teacher")):
        user = None
    return {
        "user": public_user(user),
        "csrf": csrf_token(),
        "google": google_login.google is not None,
        "classroom_id": browser_state().get("classroom_id"),
    }


@router.post("/login")
async def login(payload: Login, request: Request):
    check_csrf(request.headers.get("X-CSRF-Token", ""))
    ip = request.client.host if request.client else "unknown"
    if rate_limit.login_retry_after(ip, payload.email) > 0:
        raise HTTPException(429, "Too many attempts. Please wait before trying again.")
    rate_limit.record_login_failure(ip, payload.email)
    user = await run.io_bound(authenticate_login, payload.email, payload.password)
    if not user:
        raise HTTPException(401, "The email or password is incorrect.")
    rate_limit.record_login_success(ip, payload.email)
    set_session_user(user, payload.remember)
    request.session["remember"] = payload.remember
    return {"user": public_user(user), "csrf": csrf_token()}


@router.post("/logout")
def logout(request: Request, actor: Annotated[dict, Depends(write_staff)]):
    clear_session()
    request.session["remember"] = False
    browser_state().pop("admin_csrf", None)
    return {"ok": True}


@router.get("/profile")
def profile(actor: Annotated[dict, Depends(staff)]):
    return public_user(actor)


@router.put("/profile")
async def rename(payload: Profile, actor: Annotated[dict, Depends(write_staff)]):
    from backend.db.admin_profile import update_admin_name
    from backend.db.teacher_profile import update_teacher_name

    name = await perform(
        update_admin_name if actor["role"] == "admin" else update_teacher_name,
        actor["id"],
        payload.username,
    )
    browser_state()["auth"] = {**browser_state()["auth"], "username": name}
    return public_user(get_user_by_id(actor["id"]))


@router.put("/profile/password")
async def password(payload: Password, actor: Annotated[dict, Depends(write_staff)]):
    if not await run.io_bound(verify_password_by_id, actor["id"], payload.current):
        raise HTTPException(400, "Your current password is incorrect.")
    await perform(update_password, actor["id"], payload.password)
    return {"ok": True}
