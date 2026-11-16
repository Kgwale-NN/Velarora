"""Google OpenID Connect sign-in using the same Velarora browser session."""
import os
import secrets
import time

from authlib.integrations.starlette_client import OAuth
from authlib.integrations.base_client.errors import OAuthError
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from httpx import HTTPError
from joserfc.errors import JoseError
from nicegui import app

from backend.core.auth import set_session_user
from backend.db.google_account import google_account

router = APIRouter(include_in_schema=False)
callback_url = os.getenv("GOOGLE_REDIRECT_URI") or "http://127.0.0.1:8080/auth/google/callback"
google = None
if os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"):
    google = OAuth().register(
        name="google", client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email", "code_challenge_method": "S256", "timeout": 10},
    )


def redirect(path):
    return RedirectResponse(path, status_code=303, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})


@router.get("/auth/google")
async def start_google(request: Request, remember: bool = False):
    if google is None:
        return redirect("/login?google=unavailable")
    state = secrets.token_urlsafe(32)
    app.storage.user["google_attempt"] = {"state": state, "until": time.time() + 600, "remember": remember}
    try:
        return await google.authorize_redirect(request, callback_url, state=state, prompt="select_account")
    except (OAuthError, HTTPError, ValueError):
        return redirect("/login?google=failed")


@router.get("/auth/google/callback")
async def finish_google(request: Request):
    attempt = app.storage.user.pop("google_attempt", None)
    if not google or not attempt or attempt["until"] < time.time() or request.query_params.get("state") != attempt["state"]:
        return redirect("/login?google=failed")
    try:
        token = await google.authorize_access_token(request)
        user = google_account(token.get("userinfo") or {}) if token.get("id_token") else None
    except (OAuthError, HTTPError, JoseError, ValueError):
        return redirect("/login?google=failed")
    if not user:
        return redirect("/login?google=denied")
    set_session_user(user, remember=attempt["remember"])
    return redirect("/auth/continue")
