"""Labelled glass fields shared by account forms."""
from nicegui import ui
from frontend.pages.password_field import new_password_field


def text_field(label, *, icon, classes="", password=False, new_password=False, value="", props=""):
    with ui.column().classes("glass-field " + classes):
        ui.label(label).classes("glass-field-label")
        field = new_password_field(None) if new_password else ui.input(
            value=value, password=password, password_toggle_button=password,
        )
        field.props(f'outlined dense aria-label="{label}" ' + props).classes("glass-input w-full")
        if not new_password:
            field.props("hide-bottom-space")
        with field.add_slot("prepend"):
            ui.icon(icon)
    return field


def select_field(label, options, *, value=None, icon="badge", classes=""):
    with ui.column().classes("glass-field " + classes):
        ui.label(label).classes("glass-field-label")
        field = ui.select(options, value=value).props(
            f'outlined dense hide-bottom-space aria-label="{label}"'
        ).classes("glass-input w-full")
        with field.add_slot("prepend"):
            ui.icon(icon)
    return field
