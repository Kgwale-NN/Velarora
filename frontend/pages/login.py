"""
frontend/pages/login.py
──────────────────
Login page  /login
No nav bar — shown to unauthenticated users.
Redirects teacher → /   (dashboard)
Student monitoring records cannot sign in.

Brute-force protection: failed attempts are rate-limited per client IP AND
per username (see backend/core/rate_limit.py), so a shared-IP lab can't be
locked out wholesale and a distributed guesser is still throttled per
account. The check runs server-side in do_login, so it cannot be bypassed
by reloading the page.
"""
from pathlib import Path

from fastapi import Request
from fastapi.responses import RedirectResponse
from nicegui import app, run, ui

from backend.core import rate_limit
from backend.core.auth import get_session_user, home_path_for, set_session_user
from backend.db.staff_email import authenticate_login
from backend.core import google_login
from frontend.translate import t
from frontend.pages.page_style import page_style
from frontend.pages.design_assets import stylesheet

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

    stylesheet("login.css")
    ui.query("body").classes(add="velarora-login-page")
    page_style("login")
    with ui.dialog() as help_dialog, ui.card().classes("login-help-dialog"):
        ui.label("Need help signing in?").classes("text-lg font-semibold")
        ui.label("Ask your Velarora administrator to help you reset your password.")
        ui.button("Back to sign in", on_click=help_dialog.close).props("flat no-caps")

    with ui.element("main").classes("login-scene"):
        with ui.column().classes("login-glass"):
            ui.label("Velarora").classes("login-brand")
            ui.label("Log in to your exam workspace.").classes("login-heading")
            with ui.column().classes("login-fields"):
                ui.label(t("staff_email")).classes("login-field-label")
                email = ui.input(placeholder="Enter your email address").props(
                    'type=email autocomplete=username outlined dense hide-bottom-space aria-label="Email address"'
                ).classes("login-input")
                with email.add_slot("prepend"):
                    ui.icon("mail_outline")
                ui.label(t("login_password")).classes("login-field-label")
                password = ui.input(
                    placeholder="Enter your password", password=True, password_toggle_button=True,
                ).props('outlined dense hide-bottom-space autocomplete=current-password aria-label="Password"').classes("login-input")
                with password.add_slot("prepend"):
                    ui.icon("lock_outline")
            with ui.row().classes("login-options"):
                remember = ui.checkbox("Remember me", value=False).classes("login-remember")
                remember.tooltip("Keep me signed in for up to 30 days on this computer.")
                ui.link("Forgot password?", "#").classes("login-help").on(
                    "click.prevent", help_dialog.open)
            error = ui.label("").classes("login-error").props('role=alert aria-live=polite')

            # Captured at page build; the websocket callback below reuses it.
            client_ip = request.client.host if request.client else "unknown"

            async def do_login() -> None:
                if login_button._props.get("loading"):
                    return
                uname = email.value.strip()
                wait = rate_limit.login_retry_after(client_ip, uname)
                if wait > 0:
                    error.set_text(
                        t("login_rate_limited").format(s=int(wait) + 1))
                    password.set_value("")
                    return
                # Count in-flight attempts before yielding to the password worker.
                rate_limit.record_login_failure(client_ip, uname)
                login_button.props("loading")
                try:
                    u = await run.io_bound(authenticate_login, uname, password.value)
                finally:
                    login_button.props(remove="loading")
                if u is None:
                    error.set_text(t("login_invalid"))
                    password.set_value("")
                    return
                rate_limit.record_login_success(client_ip, uname)
                set_session_user(u, remember=bool(remember.value))
                ui.navigate.to("/auth/continue")

            login_button = ui.button("Sign in", on_click=do_login).props(
                "unelevated no-caps"
            ).props(remove="color").classes("login-submit")
            ui.label("or continue with").classes("login-divider")
            google_button = ui.button(on_click=lambda: ui.navigate.to(
                "/auth/google?remember=" + ("true" if remember.value else "false")
            )).props('unelevated no-caps aria-label="Continue with Google"').props(remove="color").classes("login-google")
            with google_button:
                ui.image(str(Path(__file__).parents[1] / "assets" / "google-mark.png")).classes("w-5 h-5 mr-3").props('alt="" aria-hidden=true')
                ui.label("Google")
            if google_login.google is None:
                google_button.disable()
                ui.label(t("google_unavailable")).classes("login-note")
            issue = request.query_params.get("google")
            if issue in ("failed", "denied", "unavailable", "credentials", "cancelled", "expired", "session", "network"):
                error.set_text(t("google_" + issue))

            # Allow pressing Enter in the password field to submit
            password.on("keydown.enter", do_login)
            email.on("keydown.enter", lambda: password.run_method("focus"))
