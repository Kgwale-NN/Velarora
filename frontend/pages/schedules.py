"""Weekly monitoring schedules with shared glass controls and confirmation dialogs."""
import logging
from nicegui import run, ui
from backend.core.auth import require_auth
from backend.db.database import list_schedules, get_schedule, delete_schedule, log_action
from frontend.pages._nav import nav
from frontend.pages.admin_shell import toast
from frontend.pages.design_assets import stylesheet
from frontend.pages.glass_fields import text_field
from frontend.pages.schedule_editor import schedule_editor, day_labels
from frontend.translate import t


def _fmt_days(value):
    labels = day_labels()
    return ', '.join(labels.get(day, day) for day in value.split(',') if day)


@ui.page('/schedules')
def page_schedules():
    current = require_auth(required_role='teacher')
    if current is None:
        return
    nav(current)
    stylesheet('schedules.css')
    busy, pending = [False], [None]
    with ui.column().classes('schedules-dashboard w-full'):
        with ui.row().classes('schedules-heading w-full items-center justify-between'):
            with ui.column().classes('schedules-heading-copy'):
                ui.label(t('schedules_title')).classes('schedules-title')
                ui.label('Set weekly exam times for each computer group.').classes('schedules-subtitle')
            new_button = ui.button('New schedule', icon='add').props('no-caps')
        with ui.card().classes('schedules-explainer w-full'):
            ui.icon('schedule').classes('schedules-section-icon')
            ui.label('Weekly times follow this computer\'s local clock. Keep Velarora running for automatic monitoring.').classes('schedules-help')
        with ui.element('div').classes('schedules-stats w-full'):
            totals = []
            for label,icon in [('Schedules','event'),('Enabled','event_available'),('Paused','pause_circle_outline')]:
                with ui.card().classes('schedule-stat-card user-stat-card'):
                    with ui.row().classes('w-full items-center justify-between gap-3'):
                        ui.label(label).classes('schedule-stat-label')
                        ui.icon(icon).classes('schedules-section-icon')
                    totals.append(ui.label('—').classes('schedule-stat-value'))
        with ui.card().classes('schedules-toolbar w-full'):
            with ui.element('div').classes('schedules-search'):
                search = text_field('Find a schedule', icon='search', placeholder='Search a name, group or model', props='debounce=150')
            refresh_button = ui.button('Refresh', icon='refresh').props('no-caps')
        columns = [{'name':name,'label':label,'field':name,'align':'left','sortable':name not in ('days','notify','actions')} for name,label in [
            ('name','Schedule'),('group_name','Group'),('model_label','Model'),('days','Days'),('time_range','Time'),
            ('notify','Alert rules'),('status','Status'),('actions','Manage')]]
        table = ui.table(columns=columns, rows=[], row_key='id', pagination={'rowsPerPage':0}).classes('schedules-table w-full')
        table.props('flat bordered hide-pagination')
        table.bind_filter_from(search,'value')
        table.add_slot('no-data', '''
            <div class="schedules-empty column items-center w-full"><q-icon name="event" size="40px" />
                <div class="schedules-empty-title">No schedules found</div>
                <div>Create a schedule or try a different search.</div>
            </div>''')
        table.add_slot('body-cell-status', '''
            <q-td :props="props"><q-badge class="schedule-status" :class="{'is-enabled': props.row.is_active}">
                {{props.row.status}}</q-badge></q-td>''')
        table.add_slot('body-cell-actions', '''
            <q-td :props="props"><div class="schedule-row-actions">
                <q-btn flat round icon="edit" :aria-label="'Edit ' + props.row.name"
                    @click="$parent.$emit('edit',props.row)"><q-tooltip>Edit schedule</q-tooltip></q-btn>
                <q-btn flat round icon="delete_outline" :aria-label="'Delete ' + props.row.name"
                    @click="$parent.$emit('delete_schedule',props.row)"><q-tooltip>Delete schedule</q-tooltip></q-btn>
            </div></q-td>''')
        with ui.dialog() as delete_dialog, ui.card().classes('schedule-dialog schedule-delete-dialog'):
            with ui.row().classes('schedule-dialog-header w-full items-start justify-between'):
                ui.label('Delete schedule?').classes('schedule-dialog-title')
                ui.button(icon='close', on_click=delete_dialog.close).props('flat round aria-label="Close delete confirmation"')
            delete_name = ui.label('').classes('schedule-delete-name')
            ui.label('This removes the weekly schedule. Saved monitoring reports stay available.').classes('schedules-help')
            delete_error = ui.label('').classes('schedule-form-error').props('role=alert')
            with ui.row().classes('schedule-dialog-footer w-full justify-end gap-3'):
                ui.button('Cancel', on_click=delete_dialog.close).props('flat no-caps')
                delete_button = ui.button('Delete schedule', icon='delete_outline').props('no-caps')

    async def refresh():
        if busy[0]:
            return
        busy[0] = True
        refresh_button.props('loading')
        table.props('loading')
        try:
            schedules = await run.io_bound(list_schedules)
            rows = []
            for schedule in schedules:
                names = [n for n in (schedule.get('notify_class_names') or '').split('||') if n]
                notify = ('Custom: ' + (', '.join(names) if len(names)<=2 else f'{len(names)} classes')) if names else 'Custom: no alerts'
                rows.append({**schedule,'group_name':schedule.get('group_name') or 'All computers',
                    'model_label':schedule.get('model_name') or 'Use active model',
                    'days':_fmt_days(schedule['days_of_week']),
                    'time_range':schedule['start_time']+' – '+schedule['end_time'],
                    'notify':notify if schedule['use_custom_notify_classes'] else 'Global rules',
                    'status':'Enabled' if schedule['is_active'] else 'Paused'})
            table.rows = rows
            table.update()
            enabled_count = sum(bool(s['is_active']) for s in schedules)
            for label,value in zip(totals,[len(schedules),enabled_count,len(schedules)-enabled_count]):
                label.set_text(str(value))
        except Exception:
            logging.getLogger(__name__).exception('Schedules could not load')
            toast('Schedules could not load. Please refresh and try again.',type='negative')
        finally:
            busy[0] = False
            refresh_button.props(remove='loading')
            table.props(remove='loading')

    editor = schedule_editor(current['id'], refresh)
    new_button.on_click(lambda: editor())
    refresh_button.on_click(refresh)

    def selected(e):
        return next((s for s in table.rows if s['id']==e.args.get('id')),None)
    def open_delete(e):
        if delete_button.props.get('loading'):
            return
        pending[0] = selected(e)
        if pending[0]:
            delete_name.set_text(pending[0]['name'])
            delete_error.set_text('')
            delete_dialog.open()
    def remove(schedule):
        if get_schedule(schedule['id']) is None:
            raise ValueError('This schedule has already been deleted. Refresh the page.')
        delete_schedule(schedule['id'])
        log_action('schedule.delete',user_id=current['id'],entity='schedule',entity_id=schedule['id'],detail=f"name={schedule['name']}")
    async def confirm_delete():
        if pending[0] is None or delete_button.props.get('loading'):
            return
        delete_button.props('loading')
        try:
            await run.io_bound(remove,pending[0])
        except Exception:
            logging.getLogger(__name__).exception('Schedule deletion failed')
            delete_error.set_text('The schedule could not be deleted. Refresh and try again.')
            return
        finally:
            delete_button.props(remove='loading')
        delete_dialog.close()
        toast(t('schedules_deleted'),type='positive')
        await refresh()
    table.on('edit',lambda e: editor(selected(e)) if selected(e) else None)
    table.on('delete_schedule',open_delete)
    delete_button.on_click(confirm_delete)
    ui.timer(0.01,refresh,once=True)
