"""A glass alert switch with confirmed state and rollback on failed saves."""
from nicegui import ui
from frontend.translate import t


def status_text(enabled):
    return t('alerts_prohibited' if enabled else 'alerts_allowed').replace('\U0001f6ab', '').replace('\u2705', '').strip()


def class_row(rule, *, readonly, save):
    saved = [bool(rule['effective_enabled'])]
    pending = [False]
    with ui.card().classes('alert-rule-card w-full') as card:
        with ui.row().classes('alert-rule-identity'):
            icon = ui.icon('notifications_active' if saved[0] else 'notifications_off').classes('alert-rule-icon')
            with ui.column().classes('alert-rule-copy'):
                ui.label(rule['name']).classes('alert-rule-name')
                hint = ui.label('').classes('alert-rule-hint')
        with ui.row().classes('alert-rule-controls'):
            status = ui.label('').classes('alert-rule-status')
            toggle = ui.switch(value=saved[0]).props('color=white keep-color')
            toggle.props['aria-label'] = f"Prohibit {rule['name']}"
            if readonly:
                toggle.props('disable')
                toggle.tooltip(t('alerts_toggle_readonly_hint'))

    def render():
        status.set_text(status_text(saved[0]))
        status.classes(replace='alert-rule-status ' + ('is-prohibited' if saved[0] else 'is-allowed'))
        hint.set_text('Alert enabled for this class.' if saved[0] else 'Detections stay in History without an alert.')
        icon.props['name'] = 'notifications_active' if saved[0] else 'notifications_off'

    async def changed(e):
        enabled = bool(e.value)
        if pending[0] or enabled == saved[0] or readonly:
            return
        pending[0] = True
        toggle.props('disable')
        hint.set_text('Saving change...')
        try:
            if await save(rule['class_id'], enabled):
                saved[0] = enabled
            else:
                toggle.set_value(saved[0])
        finally:
            pending[0] = False
            render()
            if not readonly:
                toggle.props(remove='disable')

    render()
    if not readonly:
        toggle.on_value_change(changed)
    return card
