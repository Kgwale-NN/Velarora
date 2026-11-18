"""
frontend/pages/_nav.py
─────────────────
Shared navigation bar — role-aware.

Roles
─────
  admin   — Users, Models, Audit Log, Admin Profile, Settings
  teacher — Dashboard, History, Analytics, Reports, Alert Rules, Groups,
            Schedules, My Profile
            + Start/Stop monitor + notification bell
  student — My History, My Analytics
"""
from __future__ import annotations

from nicegui import app as nicegui_app, run, ui

from backend.core.auth import clear_session
from frontend.pages.glass_fields import text_field
from frontend.translate import t, get_lang, set_lang


def nav(current_user: dict) -> None:
    role = current_user["role"]

    if role in ("admin", "teacher"):
        from frontend.pages.admin_shell import workspace_nav
        workspace_nav(current_user)
        return

    dark = ui.dark_mode()
    dark.enable() if nicegui_app.storage.user.get("dark_mode", True) else dark.disable()
    with ui.header().classes("bg-gray-900 text-white px-4 py-2 flex items-center gap-4 shadow-md"):
        ui.label("🎓 Velarora").classes("font-bold text-base mr-2")
        for key, path in [("nav_my_history", "/history"), ("nav_my_analytics", "/analytics")]:
            ui.link(t(key), path).classes("text-gray-300 hover:text-white text-sm no-underline")
        with ui.row().classes("ml-auto items-center"):
            _user_menu(current_user, dark)


# ── User menu ─────────────────────────────────────────────────────────────────

def _user_menu(current_user: dict, dark, on_logout=None):
    role = current_user["role"]

    pwd_dlg = password_dialog(current_user)

    role_label = t(f"users_role_{role}")
    label_text = f"{current_user['username']}  ({role_label})"
    with ui.dropdown_button(
        label_text, icon="account_circle",
    ).props("flat no-caps dense color=white") as account_menu:

        with ui.menu_item():
            with ui.row().classes("items-center gap-3 w-full"):
                ui.icon("dark_mode").classes("text-base")
                ui.label(t("nav_dark_mode")).classes("text-sm flex-1")
                ui.switch(
                    value=nicegui_app.storage.user.get("dark_mode", True),
                    on_change=lambda e: (
                        nicegui_app.storage.user.__setitem__("dark_mode", e.value),
                        dark.enable() if e.value else dark.disable(),
                    ),
                ).props("dense")

        ui.separator()

        # ── Language switcher ──────────────────────────────────────────────────
        with ui.menu_item():
            with ui.row().classes("items-center gap-3 w-full"):
                ui.icon("translate").classes("text-base")
                ui.label("EN / LT").classes("text-sm flex-1")
                lang_now = get_lang()
                ui.toggle(
                    {"en": "EN", "lt": "LT"},
                    value=lang_now,
                    on_change=lambda e: (set_lang(e.value), ui.navigate.reload()),
                ).props("dense")

        ui.separator()

        if role == 'teacher':
            with ui.menu_item(on_click=lambda: ui.navigate.to('/teacher-profile')):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('person_outline').classes('text-base')
                    ui.label('My Profile').classes('text-sm')
            ui.separator()

        with ui.menu_item(on_click=pwd_dlg.open):
            with ui.row().classes("items-center gap-3"):
                ui.icon("lock").classes("text-base")
                ui.label(t("nav_change_password")).classes("text-sm")

        ui.separator()

        with ui.menu_item(
            on_click=on_logout or (lambda: (clear_session(), ui.navigate.to("/auth/continue")))
        ):
            with ui.row().classes("items-center gap-3 text-red-400"):
                ui.icon("logout").classes("text-base")
                ui.label(t("nav_sign_out")).classes("text-sm")

    account_menu.bind_text_from(nicegui_app.storage.user, 'auth', backward=lambda account:
        f"{(account or current_user)['username']}  ({role_label})")
    return account_menu


def password_dialog(current_user: dict):
    from frontend.pages.design_assets import stylesheet
    stylesheet('teacher-profile.css')
    with ui.dialog() as pwd_dlg, ui.card().classes('account-password-dialog'):
        with ui.row().classes('account-dialog-heading w-full items-start justify-between'):
            ui.label(t('pwd_title')).classes('account-dialog-title')
            ui.button(icon='close',on_click=pwd_dlg.close).props('flat round aria-label="Close password dialog"')
        current_pw = text_field(t("pwd_current"), icon="lock_outline", password=True,
                                props="autocomplete=current-password", placeholder="Enter your current password")
        new_pw = text_field(t("pwd_new"), icon="lock_outline", new_password=True, placeholder="Create a strong password")
        confirm_pw = text_field(t("pwd_confirm"), icon="lock_outline", password=True,
                                props="autocomplete=new-password", placeholder="Re-enter your new password")
        err_lbl = ui.label("").classes("account-form-error").props("role=alert")

        async def do_change() -> None:
            from backend.db.database import validate_password, update_password
            from backend.db.user_queries import verify_password_by_id
            if save_password._props.get("loading"):
                return
            old_value, new_value, confirmation = current_pw.value, new_pw.value, confirm_pw.value
            save_password.props("loading")
            try:
                if not await run.io_bound(verify_password_by_id, current_user["id"], old_value):
                    err_lbl.set_text(t("pwd_err_wrong"))
                    return
                try:
                    validate_password(new_value)
                except ValueError as exc:
                    err_lbl.set_text(str(exc))
                    return
                if new_value != confirmation:
                    err_lbl.set_text(t("pwd_err_mismatch"))
                    return
                await run.io_bound(update_password, current_user["id"], new_value)
                pwd_dlg.close()
                current_pw.set_value("")
                new_pw.set_value("")
                confirm_pw.set_value("")
                err_lbl.set_text("")
                from frontend.pages.admin_shell import toast
                toast(t("pwd_success"), type="positive")
            except Exception:
                import logging
                logging.getLogger(__name__).exception('Password change failed')
                err_lbl.set_text('The password could not be changed. Please try again.')
            finally:
                save_password.props(remove="loading")

        with ui.row().classes('account-dialog-footer w-full justify-end gap-3'):
            ui.button(t('pwd_cancel'),on_click=pwd_dlg.close).props('flat no-caps')
            save_password = ui.button(t('pwd_save'),icon='check',on_click=do_change).props('no-caps')

    return pwd_dlg


# ── Notification bell ─────────────────────────────────────────────────────────

def _notification_bell() -> None:
    from frontend.pages.notification_panel import notification_bell
    notification_bell()
