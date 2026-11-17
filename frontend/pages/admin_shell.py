"""Shared glass admin frame and navigation."""
from pathlib import Path
from nicegui import ui
from backend.core.auth import clear_session
from frontend.pages.page_style import page_style


def toast(message, **options):
    options.setdefault("position", "top-right")
    options.setdefault("close_button", True)
    options.setdefault("classes", "velarora-toast")
    ui.notify(message, **options)


def admin_nav(user):
    ui.dark_mode().enable()
    ui.query("body").classes(add="admin-glass-page")
    ui.add_css((Path(__file__).parents[1] / "assets" / "admin.css").read_text())
    page_style("admin")
    with ui.dialog() as logout, ui.card().classes("admin-confirm"):
        ui.icon("logout").classes("text-3xl")
        ui.label("Log out of Velarora?").classes("text-xl font-semibold")
        ui.label("You will return to the sign-in page.").classes("text-sm text-gray-300")
        with ui.row().classes("w-full justify-end gap-3 mt-3"):
            ui.button("Cancel", on_click=logout.close).props("flat no-caps")
            ui.button("Log out", on_click=lambda: (
                clear_session(), ui.navigate.to("/auth/continue")
            )).props("no-caps").classes("admin-logout-confirm")
    current = ui.context.client.page.path
    links = [("Users", "people_outline", "/users"), ("Models", "view_in_ar", "/models"),
             ("Audit Log", "history", "/audit"), ("Admin Profile", "person_outline", "/profile"),
             ("Settings", "settings", "/settings")]
    with ui.left_drawer(value=False).props("overlay bordered width=270").classes("admin-drawer") as drawer:
        with ui.row().classes("items-center justify-between w-full px-3 py-5"):
            ui.label("Velarora").classes("text-xl font-semibold italic")
            ui.button(icon="close", on_click=lambda: drawer.hide()).props(
                'flat round dense aria-label="Close menu"')
        ui.label("ADMINISTRATION").classes("admin-menu-caption")
        for label, icon, path in links:
            with ui.link(target=path).classes("admin-nav-link" + (" active" if current == path else "")):
                ui.icon(icon).classes("text-xl")
                ui.label(label)
        ui.space()
        ui.separator()
        ui.button("Log out", icon="logout", on_click=logout.open).props(
            "flat no-caps align=left").classes("admin-signout w-full")
    with ui.header().classes("admin-header"):
        menu_button = ui.button(icon="menu", on_click=drawer.toggle).props(
            'flat round aria-label="Open menu" aria-expanded="false"').classes("admin-menu-button")
        ui.link("Velarora", "/users").classes("admin-brand")
        ui.label(next((label for label, _, path in links if path == current), "Administration")).classes("admin-page-title")
        ui.space()
        with ui.link(target="/profile").classes("admin-account"):
            ui.icon("account_circle").classes("text-2xl")
            ui.label(user["username"]).classes("admin-account-name")

    drawer.on_value_change(lambda e: menu_button.props(
        "aria-expanded=true" if e.value else "aria-expanded=false"))
