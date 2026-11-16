"""
frontend/pages/login.py
──────────────────
Login page  /login
No nav bar — shown to unauthenticated users.
Redirects teacher → /   (dashboard)
Redirects student → /history

Brute-force protection: failed attempts are rate-limited per client IP AND
per username (see backend/core/rate_limit.py), so a shared-IP lab can't be
locked out wholesale and a distributed guesser is still throttled per
account. The check runs server-side in do_login, so it cannot be bypassed
by reloading the page.
"""
from fastapi import Request
from fastapi.responses import RedirectResponse
from nicegui import app, ui

from backend.core import rate_limit
from backend.core.auth import get_session_user, home_path_for, set_session_user
from backend.db.staff_email import authenticate_login
from backend.core import google_login
from frontend.translate import t

app.include_router(google_login.router)


@app.get("/auth/continue", include_in_schema=False)
def finish_sign_in(request: Request):
    user = get_session_user()
    request.session["remember"] = bool(user and app.storage.user.get("remember_until"))
    return RedirectResponse(home_path_for(user) if user else "/login", headers={"Cache-Control": "no-store"})


@ui.page("/login")
def page_login(request: Request) -> None:
    # Already logged in → skip
    user = get_session_user()
    if user:
        ui.navigate.to(home_path_for(user))
        return

    with ui.column().classes(
        "absolute-center items-center gap-4 w-full"
    ).style("max-width: 360px; margin: auto;"):

        ui.label(t("login_title")).classes("text-2xl font-bold text-center")
        ui.label(t("login_subtitle")).classes("text-gray-400 text-sm mb-2")

        with ui.card().classes("w-full gap-3 p-6"):
            email = ui.input(t("staff_email")).props(
                "type=email autocomplete=username outlined dense autofocus"
            ).classes("w-full")
            password = ui.input(
                t("login_password"), password=True, password_toggle_button=True,
            ).props("outlined dense autocomplete=current-password").classes("w-full")
            remember = ui.checkbox(t("login_remember"), value=False)
            error    = ui.label("").classes("text-red-400 text-sm")

            # Captured at page build; the websocket callback below reuses it.
            client_ip = request.client.host if request.client else "unknown"

            def do_login() -> None:
                uname = email.value.strip()
                wait = rate_limit.login_retry_after(client_ip, uname)
                if wait > 0:
                    error.set_text(
                        t("login_rate_limited").format(s=int(wait) + 1))
                    password.set_value("")
                    return
                u = authenticate_login(uname, password.value)
                if u is None:
                    rate_limit.record_login_failure(client_ip, uname)
                    error.set_text(t("login_invalid"))
                    password.set_value("")
                    return
                rate_limit.record_login_success(client_ip, uname)
                set_session_user(u, remember=bool(remember.value))
                ui.navigate.to("/auth/continue")

            ui.button(t("login_btn"), on_click=do_login).props(
                "color=primary"
            ).classes("w-full mt-2")

            google_button = ui.button(t("google_continue"), on_click=lambda: ui.navigate.to(
                "/auth/google?remember=" + ("true" if remember.value else "false")
            )).props("outline").classes("w-full")
            if google_login.google is None:
                google_button.disable()
                ui.label(t("google_unavailable")).classes("text-xs")
            issue = request.query_params.get("google")
            if issue in ("failed", "denied", "unavailable"):
                error.set_text(t("google_" + issue))

            # Allow pressing Enter in the password field to submit
            password.on("keydown.enter", do_login)
            email.on("keydown.enter", lambda: password.run_method("focus"))
