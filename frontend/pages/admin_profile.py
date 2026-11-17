"""Administrator profile and the existing password change flow."""
from nicegui import app, ui
from backend.core.auth import require_auth
from backend.db.user_queries import get_user_by_id
from backend.db.admin_profile import update_admin_name
from frontend.pages._nav import nav, password_dialog
from frontend.pages.admin_shell import toast


@ui.page("/profile")
def admin_profile():
    current = require_auth("admin")
    if not current:
        return
    nav(current)
    user = get_user_by_id(current["id"])
    dialog = password_dialog(current)
    with ui.column().classes("admin-profile mx-auto w-full"):
        ui.label("Admin Profile").classes("text-2xl font-semibold")
        with ui.card().classes("w-full p-6 gap-5"):
            ui.icon("person_outline").classes("text-5xl")
            name = ui.input("Username", value=user["username"]).props("outlined stack-label").classes("w-full")
            error = ui.label("").classes("text-sm text-red-300")

            def save_name():
                try:
                    saved = update_admin_name(current["id"], name.value)
                except ValueError as exc:
                    error.set_text(str(exc))
                    return
                app.storage.user["auth"] = {**current, "username": saved}
                toast("Profile saved.", type="positive")
                ui.navigate.reload()

            ui.input("Email address", value=user["email"] or "").props("readonly outlined").classes("w-full")
            ui.input("Role", value="Administrator").props("readonly outlined").classes("w-full")
            with ui.row().classes("gap-3"):
                ui.button("Save profile", icon="check", on_click=save_name).props("no-caps")
                ui.button("Change password", icon="lock_outline", on_click=dialog.open).props("outline no-caps")
