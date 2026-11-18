"""Shared role-aware glass frame for administrators and teachers."""
from nicegui import ui
from backend.core.auth import clear_session
from frontend.pages.page_style import page_style
from frontend.pages.design_assets import stylesheet


def toast(message, **options):
    kind = options.pop("type", None) or "info"
    icons = {"positive": "check_circle_outline", "negative": "error_outline",
             "warning": "info_outline", "info": "info_outline"}
    classes = options.pop("classes", "")
    settings = {
        "message": str(message), "position": options.pop("position", "top-right"),
        "closeBtn": options.pop("close_button", True), "group": False,
        "timeout": options.pop("timeout", 0 if kind == "ongoing" else 4500),
        "classes": f"velarora-toast velarora-toast--{kind} {classes}",
        "attrs": {"role": "alert" if kind == "negative" else "status"},
    }
    if kind != "ongoing":
        settings["icon"] = icons.get(kind, "info_outline")
    settings.update(options)
    return ui.notification(options=settings)


def workspace_nav(user):
    teacher = user["role"] == "teacher"
    dark = ui.dark_mode()
    dark.enable()
    ui.query("body").classes(add="admin-glass-page" + (" teacher-workspace" if teacher else ""))
    stylesheet("admin.css")
    page_style("admin")
    with ui.dialog() as logout, ui.card().classes("admin-confirm"):
        ui.label("Log out of Velarora?").classes("text-xl font-semibold")
        ui.label("You will return to the sign-in page.").classes("text-sm text-gray-300")
        with ui.row().classes("w-full justify-end gap-3 mt-3"):
            ui.button("Cancel", on_click=logout.close).props("flat no-caps")
            ui.button("Log out", on_click=lambda: (
                clear_session(), ui.navigate.to("/auth/continue")
            )).props("no-caps").classes("admin-logout-confirm")
    current = ui.context.client.page.path
    if teacher:
        links = [
            ("Dashboard", "dashboard", "/"), ("History", "history", "/history"),
            ("Analytics", "insights", "/analytics"), ("Reports", "description", "/reports"),
            ("Alert Rules", "notifications_active", "/alerts"), ("Groups", "groups", "/groups"),
            ("Schedules", "event", "/schedules"), ("My Profile", "person_outline", "/teacher-profile"),
        ]
    else:
        links = [("Users", "people_outline", "/users"), ("Models", "view_in_ar", "/models"),
                 ("Audit Log", "history", "/audit"), ("Admin Profile", "person_outline", "/profile"),
                 ("Settings", "settings", "/settings")]
    home = "/" if teacher else "/users"
    with ui.left_drawer(value=False).props("overlay bordered width=270").classes("admin-drawer") as drawer:
        with ui.row().classes("items-center justify-between w-full px-3 py-5"):
            ui.label("Velarora").classes("text-xl font-semibold italic")
            ui.button(icon="close", on_click=lambda: drawer.hide()).props(
                'flat round dense aria-label="Close menu"')
        ui.label("TEACHER WORKSPACE" if teacher else "ADMINISTRATION").classes("admin-menu-caption")
        for label, icon, path in links:
            with ui.link(target=path).classes("admin-nav-link" + (" active" if current == path else "")):
                ui.icon(icon).classes("text-xl")
                ui.label(label)
        ui.space()
        ui.separator()
        ui.button("Log out", icon="logout", on_click=logout.open).props(
            "flat no-caps align=left").classes("admin-signout w-full")
    with ui.header().classes("admin-header" + (" teacher-header" if teacher else "")):
        def toggle_menu():
            drawer.toggle()
            ui.run_javascript(f"""
                const button = document.getElementById('{menu_button.html_id}');
                button.classList.remove('menu-turn');
                void button.offsetWidth;
                button.classList.add('menu-turn');
            """)
        menu_button = ui.button(icon="menu", on_click=toggle_menu).props(
            'flat round aria-label="Open menu" aria-expanded="false"').classes("admin-menu-button")
        ui.link("Velarora", home).classes("admin-brand")
        ui.label(next((label for label, _, path in links if path == current), "Administration")).classes("admin-page-title")
        ui.space()
        if teacher:
            from frontend.pages._nav import _notification_bell, _user_menu
            _notification_bell()
            _user_menu(user, dark, on_logout=logout.open).classes("teacher-account-menu")
        else:
            with ui.link(target="/profile").classes("admin-account"):
                ui.icon("account_circle").classes("text-2xl")
                ui.label(user["username"]).classes("admin-account-name")
        if teacher:
            from frontend.pages.teacher_toolbar import monitoring_controls
            with ui.row().classes("teacher-monitor-toolbar w-full items-center gap-3"):
                monitoring_controls(user)
                ui.space()

    drawer.on_value_change(lambda e: menu_button.props(
        "aria-expanded=true" if e.value else "aria-expanded=false"))
