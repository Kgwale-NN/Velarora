"""Administrator profile, using the existing password change flow."""
from nicegui import ui
from backend.core.auth import require_auth
from backend.db.user_queries import get_user_by_id
from frontend.pages._nav import nav, password_dialog


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
            ui.icon("account_circle").classes("text-5xl")
            ui.label(user["username"]).classes("text-xl")
            for label, value in [("Email address", user["email"]), ("Role", "Administrator")]:
                ui.input(label, value=value or "").props("readonly outlined").classes("w-full")
            ui.button("Change password", icon="lock_outline", on_click=dialog.open).props("no-caps")
