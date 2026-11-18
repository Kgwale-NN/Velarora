"""Glass schedule editor with explicit model and notification policy choices."""
import logging
from nicegui import run, ui
from backend.db.schedule_editor_data import editor_choices
from backend.db.schedule_editor_save import save_editor_schedule
from frontend.pages.admin_shell import toast
from frontend.pages.glass_fields import select_field, text_field
from frontend.translate import t


def day_labels():
    return {str(i): t('schedules_day_' + day) for i, day in enumerate(['mon','tue','wed','thu','fri','sat','sun'])}


def schedule_editor(user_id, refresh):
    editing, choices, generation = [None], [None], [0]
    loading = [False]
    checks = {}
    with ui.dialog() as dialog, ui.card().classes('schedule-dialog'):
        with ui.row().classes('schedule-dialog-header w-full items-start justify-between'):
            title = ui.label(t('schedules_new')).classes('schedule-dialog-title')
            ui.button(icon='close', on_click=dialog.close).props('flat round aria-label="Close schedule dialog"')
        with ui.column().classes('schedule-dialog-body w-full'):
            with ui.column().classes('schedule-loading w-full') as placeholders:
                for _ in range(3):
                    ui.skeleton().classes('schedule-skeleton w-full')
            with ui.column().classes('schedule-fields w-full') as fields:
                name = text_field(t('schedules_field_name'), icon='event_note', placeholder='e.g. Morning exam')
                group = select_field(t('schedules_field_group'), {'':'All computers'}, value='', icon='groups')
                model = select_field(t('schedules_field_model'), {'':'Use active model'}, value='', icon='view_in_ar')
                ui.label('Days of week').classes('schedule-field-heading')
                with ui.element('div').classes('schedule-days w-full'):
                    days = {key: ui.checkbox(label, value=int(key)<5).props('color=white keep-color') for key,label in day_labels().items()}
                with ui.element('div').classes('schedule-times w-full'):
                    start = text_field(t('schedules_start_time'), value='08:00', icon='schedule', props='type=time step=60')
                    end = text_field(t('schedules_end_time'), value='14:00', icon='schedule', props='type=time step=60')
                ui.label('Start and end times are on the same day, using this computer\'s local clock.').classes('schedules-help')
                enabled = ui.switch('Schedule enabled', value=True).props('color=white keep-color')
                ui.separator()
                custom = ui.switch('Use custom alert rules', value=False).props('color=white keep-color')
                policy_hint = ui.label('').classes('schedules-help')
                class_area = ui.column().classes('schedule-class-choices w-full')
            error = ui.label('').classes('schedule-form-error').props('role=alert')
        with ui.row().classes('schedule-dialog-footer w-full justify-end gap-3'):
            ui.button(t('schedules_cancel'), on_click=dialog.close).props('flat no-caps')
            save_button = ui.button(t('schedules_save'), icon='check').props('no-caps disable')
    fields.set_visibility(False)

    def policy():
        class_area.set_visibility(bool(custom.value))
        if not custom.value:
            policy_hint.set_text('Uses the global rules on Alert Rules.')
        else:
            count = sum(bool(cb.value) for cb in checks.values())
            policy_hint.set_text(f'{count} class(es) selected to raise alerts.' if count else
                                 'No classes selected: this schedule will not raise detection alerts.')

    def rebuild(selected=None):
        if choices[0] is None:
            return
        if selected is None:
            selected = {cid for cid, cb in checks.items() if cb.value}
        mid = int(model.value) if model.value else (choices[0]['active'] or {}).get('id')
        checks.clear()
        class_area.clear()
        with class_area:
            visible = choices[0]['classes'].get(mid, [])
            if not visible:
                ui.label('No classes are available for this model yet.').classes('schedules-help')
            for cls in visible:
                cb = ui.checkbox(cls['name'], value=cls['id'] in selected).props('color=white keep-color')
                cb.on_value_change(policy)
                checks[cls['id']] = cb
        policy()

    model.on_value_change(lambda: None if loading[0] else rebuild())
    custom.on_value_change(policy)

    async def open_editor(schedule=None):
        if save_button.props.get('loading'):
            return
        generation[0] += 1
        token = generation[0]
        loading[0] = True
        editing[0] = schedule['id'] if schedule else None
        title.set_text(t('schedules_edit').format(name=schedule['name']) if schedule else t('schedules_new'))
        fields.set_visibility(False)
        placeholders.set_visibility(True)
        error.set_text('')
        save_button.props('disable')
        dialog.open()
        try:
            data = await run.io_bound(editor_choices, editing[0])
        except Exception:
            logging.getLogger(__name__).exception('Schedule choices could not load')
            if token == generation[0]:
                error.set_text('The schedule could not load. Close this window and try again.')
                placeholders.set_visibility(False)
            return
        if token != generation[0]:
            return
        choices[0] = data
        current = data['schedule'] or {}
        group.options = {'':'All computers', **{str(g['id']):g['name'] for g in data['groups']}}
        model.options = {'':'Use active model', **{str(m['id']):m['name'] for m in data['models']}}
        group.set_value(str(current['group_id']) if current.get('group_id') is not None else
                        (str(data['groups'][0]['id']) if not current and data['groups'] else ''))
        model.set_value(str(current['model_id']) if current.get('model_id') is not None else '')
        group.update()
        model.update()
        name.set_value(current.get('name', ''))
        active_days = current.get('days_of_week', '0,1,2,3,4').split(',')
        for key, cb in days.items():
            cb.set_value(key in active_days)
        start.set_value(current.get('start_time', '08:00'))
        end.set_value(current.get('end_time', '14:00'))
        enabled.set_value(bool(current.get('is_active', True)))
        custom.set_value(bool(current.get('use_custom_notify_classes', False)))
        rebuild(set(current.get('notify_class_ids', [])))
        loading[0] = False
        placeholders.set_visibility(False)
        fields.set_visibility(True)
        save_button.props(remove='disable')

    async def save():
        if loading[0] or save_button.props.get('loading'):
            return
        payload = {'name':name.value, 'group_id':int(group.value) if group.value else None,
                   'model_id':int(model.value) if model.value else None, 'days':[k for k,cb in days.items() if cb.value],
                   'start':start.value, 'end':end.value, 'active':bool(enabled.value), 'custom':bool(custom.value),
                   'notify_ids':[cid for cid,cb in checks.items() if cb.value]}
        sid = editing[0]
        error.set_text('')
        save_button.props('loading')
        controls = [name,group,model,start,end,enabled,custom,*days.values(),*checks.values()]
        for control in controls:
            control.props('disable')
        try:
            await run.io_bound(save_editor_schedule, payload, user_id, sid)
        except ValueError as exc:
            error.set_text(str(exc))
            return
        except Exception:
            logging.getLogger(__name__).exception('Schedule save failed')
            error.set_text('The schedule could not be saved. Please try again.')
            return
        finally:
            save_button.props(remove='loading')
            for control in controls:
                control.props(remove='disable')
        dialog.close()
        toast(t('schedules_created' if sid is None else 'schedules_updated').format(name=(payload['name'] or '').strip()), type='positive')
        await refresh()

    def closed(e):
        if not e.value:
            generation[0] += 1
    dialog.on_value_change(closed)
    save_button.on_click(save)
    return open_editor
