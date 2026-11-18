"""Glass create, edit, assignment and deletion dialogs for computer groups."""
import logging
import sqlite3
from nicegui import run, ui
from backend.db.database import (create_group, update_group, delete_group, get_group,
    list_computers, list_computers_in_group, list_schedules_for_group, log_action)
from backend.db.group_membership import set_group_computers
from frontend.pages.admin_shell import toast
from frontend.pages.glass_fields import text_field
from frontend.translate import t


def _frame(title, classes=''):
    dialog = ui.dialog()
    with dialog, ui.card().classes('group-dialog ' + classes):
        with ui.row().classes('group-dialog-header w-full items-start justify-between'):
            heading = ui.label(title).classes('group-dialog-title')
            ui.button(icon='close', on_click=dialog.close).props('flat round aria-label="Close group dialog"')
        body = ui.column().classes('group-dialog-body w-full')
        footer = ui.row().classes('group-dialog-footer w-full justify-end gap-3')
    return dialog, heading, body, footer


def editor_dialog(user_id, refresh):
    dialog, title, body, footer = _frame(t('groups_new'))
    editing = [None]
    with body:
        name = text_field(t('groups_name'), icon='groups', placeholder='e.g. Lab 1')
        description = text_field(t('groups_description'), icon='notes', placeholder='Optional description')
        error = ui.label('').classes('group-form-error').props('role=alert')
    with footer:
        ui.button(t('groups_cancel'), on_click=dialog.close).props('flat no-caps')
        button = ui.button(t('groups_save'), icon='check').props('no-caps')

    def write(gid, value, details):
        if gid is None:
            gid = create_group(value, details)
            action = 'group.create'
        else:
            update_group(gid, value, details)
            action = 'group.update'
        log_action(action, user_id=user_id, entity='computer_group', entity_id=gid, detail=f'name={value}')

    async def save():
        if button.props.get('loading'):
            return
        value, details, gid = (name.value or '').strip(), (description.value or '').strip(), editing[0]
        if not value:
            error.set_text(t('groups_name_required'))
            return
        error.set_text('')
        button.props('loading')
        name.props('disable')
        description.props('disable')
        try:
            await run.io_bound(write, gid, value, details)
        except sqlite3.IntegrityError:
            error.set_text('A group with this name already exists. Choose another name.')
            return
        except ValueError as exc:
            error.set_text(str(exc))
            return
        except Exception:
            logging.getLogger(__name__).exception('Group save failed')
            error.set_text('The group could not be saved. Please try again.')
            return
        finally:
            button.props(remove='loading')
            name.props(remove='disable')
            description.props(remove='disable')
        dialog.close()
        toast(t('groups_created' if gid is None else 'groups_updated').format(name=value), type='positive')
        await refresh()

    def open_editor(group=None):
        if button.props.get('loading'):
            return
        editing[0] = group['id'] if group else None
        title.set_text(t('groups_edit').format(name=group['name']) if group else t('groups_new'))
        name.set_value(group['name'] if group else '')
        description.set_value((group.get('description') or '') if group else '')
        error.set_text('')
        dialog.open()

    button.on_click(save)
    return open_editor


def assignment_dialog(user_id, refresh):
    dialog, title, body, footer = _frame('Assign computers', 'group-assign-dialog')
    group_id = [None]
    generation = [0]
    checks = {}
    with body:
        ui.label(t('groups_assign_hint')).classes('groups-help')
        search = text_field('Find a computer', icon='search', placeholder='Search computers', props='debounce=150')
        selected_label = ui.label('').classes('groups-help').props('role=status aria-live=polite')
        choices = ui.column().classes('group-computer-choices w-full')
        empty = ui.label('No matching computers.').classes('groups-help')
        error = ui.label('').classes('group-form-error').props('role=alert')
    with footer:
        ui.button(t('groups_cancel'), on_click=dialog.close).props('flat no-caps')
        button = ui.button(t('groups_save'), icon='check').props('no-caps disable')

    def filter_choices():
        query = (search.value or '').strip().casefold()
        visible = 0
        for checkbox in checks.values():
            show = query in checkbox.text.casefold()
            checkbox.set_visibility(show)
            visible += show
        empty.set_visibility(not visible)
        selected_label.set_text(f'{sum(bool(cb.value) for cb in checks.values())} selected')

    async def open_assign(group):
        if button.props.get('loading'):
            return
        generation[0] += 1
        token = generation[0]
        group_id[0] = group['id']
        title.set_text(t('groups_assign_title').format(name=group['name']))
        button.props('disable')
        error.set_text('')
        search.set_value('')
        checks.clear()
        choices.clear()
        empty.set_visibility(False)
        selected_label.set_text('Loading computers...')
        dialog.open()
        try:
            computers, members = await run.io_bound(lambda: (list_computers(), list_computers_in_group(group['id'])))
        except Exception:
            logging.getLogger(__name__).exception('Group computers could not load')
            if token == generation[0]:
                error.set_text('Computers could not load. Close this window and try again.')
            return
        if token != generation[0]:
            return
        member_ids = {c['id'] for c in members}
        with choices:
            for computer in computers:
                checkbox = ui.checkbox(computer['name'], value=computer['id'] in member_ids).props('color=white keep-color')
                checkbox.on_value_change(filter_choices)
                checks[computer['id']] = checkbox
        empty.set_text(t('groups_no_computers') if not computers else 'No matching computers.')
        filter_choices()
        button.props(remove='disable')

    async def save():
        if button.props.get('loading') or group_id[0] is None:
            return
        gid = group_id[0]
        selected = {cid for cid, cb in checks.items() if cb.value}
        button.props('loading')
        for checkbox in checks.values():
            checkbox.props('disable')
        try:
            await run.io_bound(set_group_computers, gid, selected, user_id=user_id)
        except ValueError as exc:
            error.set_text(str(exc))
            return
        except Exception:
            logging.getLogger(__name__).exception('Group assignment failed')
            error.set_text('Assignments could not be saved. Please try again.')
            return
        finally:
            button.props(remove='loading')
            for checkbox in checks.values():
                checkbox.props(remove='disable')
        dialog.close()
        toast(t('groups_assign_saved'), type='positive')
        await refresh()

    def closed(e):
        if not e.value:
            generation[0] += 1
    dialog.on_value_change(closed)
    button.on_click(save)
    search.on_value_change(filter_choices)
    return open_assign


def delete_dialog(user_id, refresh):
    dialog, title, body, footer = _frame('Delete group?', 'group-delete-dialog')
    pending = [None]
    with body:
        name = ui.label('').classes('group-delete-name')
        note = ui.label('').classes('groups-help')
        ui.label('Computers stay registered and available in other groups.').classes('groups-help')
        error = ui.label('').classes('group-form-error').props('role=alert')
    with footer:
        ui.button(t('groups_cancel'), on_click=dialog.close).props('flat no-caps')
        button = ui.button('Delete group', icon='delete_outline').props('no-caps').classes('group-confirm-delete')

    async def open_delete(group):
        if button.props.get('loading'):
            return
        try:
            schedules = await run.io_bound(list_schedules_for_group, group['id'])
        except Exception:
            toast('The group could not be checked. Please try again.', type='negative')
            return
        pending[0] = group
        name.set_text(group['name'])
        note.set_text(f'This will also permanently delete {len(schedules)} linked schedule(s).' if schedules else
                      'This removes the group and its computer assignments.')
        error.set_text('')
        dialog.open()

    def remove(group):
        if get_group(group['id']) is None:
            raise ValueError('This group has already been deleted. Refresh the page.')
        delete_group(group['id'])
        log_action('group.delete', user_id=user_id, entity='computer_group', entity_id=group['id'], detail=f"name={group['name']}")

    async def confirm():
        if pending[0] is None or button.props.get('loading'):
            return
        button.props('loading')
        try:
            await run.io_bound(remove, pending[0])
        except Exception:
            logging.getLogger(__name__).exception('Group deletion failed')
            error.set_text('The group could not be deleted. Please refresh and try again.')
            return
        finally:
            button.props(remove='loading')
        dialog.close()
        toast(t('groups_deleted'), type='positive')
        await refresh()

    button.on_click(confirm)
    return open_delete
