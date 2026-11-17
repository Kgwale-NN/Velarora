"""Shared input for setting a new password."""
from nicegui import ui

from backend.db.user_passwords import MIN_PASSWORD_LENGTH, validate_password


def new_password_field(label: str | None):
    def feedback(value: str):
        if value:
            try:
                validate_password(value)
            except ValueError as exc:
                return str(exc)
        return None

    field = ui.input(label, password=True, password_toggle_button=True, validation=feedback)
    field.props("outlined autocomplete=new-password")
    field.classes("new-password-field")
    field.props(f'hint="At least {MIN_PASSWORD_LENGTH} characters. Start with a capital letter. Include a number and a symbol." persistent-hint')
    return field
