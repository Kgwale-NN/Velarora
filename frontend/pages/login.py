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
from nicegui import ui

from backend.core import rate_limit
from backend.core.auth import get_session_user, set_session_user
from backend.db.staff_email import authenticate_login, link_staff_email
from frontend.translate import t


@ui.page("/login")
def page_login(request: Request) -> None:
    # Already logged in → skip
    user = get_session_user()
    if user:
        if user["role"] == "admin":
            ui.navigate.to("/users")
        elif user["role"] == "student":
            ui.navigate.to("/history")
        else:
            ui.navigate.to("/")
        return

    with ui.column().classes(
        "absolute-center items-center gap-4 w-full"
    ).style("max-width: 360px; margin: auto;"):

        ui.label(t("login_title")).classes("text-2xl font-bold text-center")
        ui.label(t("login_subtitle")).classes("text-gray-400 text-sm mb-2")

        with ui.card().classes("w-full gap-3 p-6"):
            mode = ui.select({"staff": t("staff_signin"), "student": t("users_role_student"),
                              "setup": t("staff_setup")}, value="staff").classes("w-full")
            username = ui.input(t("staff_email")).props(
                "outlined dense autofocus"
            ).classes("w-full")
            setup_email = ui.input(t("staff_email")).props("outlined dense type=email").classes("w-full")
            setup_email.set_visibility(False)

            def change_mode() -> None:
                username.set_label(t("staff_email") if mode.value == "staff" else t("login_username"))
                username.set_value("")
                setup_email.set_visibility(mode.value == "setup")
                error.set_text("")
                password.set_value("")

            mode.on_value_change(lambda _: change_mode())
            password = ui.input(
                t("login_password"), password=True, password_toggle_button=True,
            ).props("outlined dense").classes("w-full")
            error    = ui.label("").classes("text-red-400 text-sm")

            # Captured at page build; the websocket callback below reuses it.
            client_ip = request.client.host if request.client else "unknown"

            def do_login() -> None:
                uname = username.value.strip()
                wait = rate_limit.login_retry_after(client_ip, uname)
                if wait > 0:
                    error.set_text(
                        t("login_rate_limited").format(s=int(wait) + 1))
                    password.set_value("")
                    return
                u = authenticate_login(uname, password.value, mode.value)
                if u is None:
                    rate_limit.record_login_failure(client_ip, uname)
                    error.set_text(t("login_invalid"))
                    password.set_value("")
                    return
                if mode.value == "setup":
                    try:
                        link_staff_email(u["id"], setup_email.value)
                    except ValueError as exc:
                        error.set_text(str(exc))
                        return
                rate_limit.record_login_success(client_ip, uname)
                set_session_user(u)
                if u["role"] == "admin":
                    ui.navigate.to("/users")
                elif u["role"] == "student":
                    ui.navigate.to("/history")
                else:
                    ui.navigate.to("/")

            ui.button(t("login_btn"), on_click=do_login).props(
                "color=primary"
            ).classes("w-full mt-2")

            # Allow pressing Enter in the password field to submit
            password.on("keydown.enter", do_login)
            username.on("keydown.enter", lambda: password.run_method("focus"))
