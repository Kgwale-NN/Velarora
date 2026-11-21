"""Computer groups: glass controls, membership editing and safe confirmation dialogs."""
import logging
from nicegui import run, ui
from backend.core.auth import require_auth
from backend.db.database import list_groups, list_computers
from frontend.pages._nav import nav
from frontend.pages.admin_shell import toast
from frontend.pages.design_assets import stylesheet
from frontend.pages.glass_fields import text_field
from frontend.pages.group_dialogs import editor_dialog, assignment_dialog, delete_dialog
from frontend.pages.group_import_tools import import_tools
from frontend.translate import t


@ui.page('/groups')
def page_groups():
    current = require_auth(required_role='admin')
    if current is None:
        return
    from backend.api.react_admin import redirect_if_built
    if redirect_if_built("classrooms"):
        return
    nav(current)
    stylesheet('groups.css')
    busy = [False]
    with ui.column().classes('groups-dashboard w-full'):
        with ui.row().classes('groups-heading w-full items-center justify-between'):
            with ui.column().classes('groups-heading-copy'):
                ui.label(t('groups_title')).classes('groups-title')
                ui.label('Organise computers by classroom or exam room.').classes('groups-subtitle')
            new_button = ui.button('New group', icon='add').props('no-caps')
        with ui.element('div').classes('groups-stats w-full'):
            totals = []
            for label, icon in [('Groups', 'groups'), ('Registered computers', 'computer')]:
                with ui.card().classes('group-stat-card user-stat-card'):
                    with ui.row().classes('w-full items-center justify-between gap-3'):
                        ui.label(label).classes('group-stat-label')
                        ui.icon(icon).classes('groups-section-icon')
                    totals.append(ui.label('—').classes('group-stat-value'))
        with ui.card().classes('groups-toolbar w-full'):
            with ui.element('div').classes('groups-search'):
                search = text_field('Find a group', icon='search', placeholder='Search a name or description', props='debounce=150')
            refresh_button = ui.button('Refresh', icon='refresh').props('no-caps')
        ui.label('A computer can belong to more than one group. Use groups when scheduling an exam.').classes('groups-help')
        columns = [
            {'name': 'name', 'label': t('groups_col_group'), 'field': 'name', 'sortable': True, 'align': 'left'},
            {'name': 'description', 'label': t('groups_col_desc'), 'field': 'description', 'align': 'left'},
            {'name': 'computer_count', 'label': t('groups_col_computers'), 'field': 'computer_count', 'sortable': True, 'align': 'center'},
            {'name': 'created_at', 'label': t('groups_col_created'), 'field': 'created_at', 'sortable': True, 'align': 'left'},
            {'name': 'actions', 'label': 'Manage', 'field': 'id', 'align': 'right'},
        ]
        table = ui.table(columns=columns, rows=[], row_key='id', pagination={'rowsPerPage': 0}).classes('groups-table w-full')
        table.props('flat bordered hide-pagination')
        table.bind_filter_from(search, 'value')
        table.add_slot('body-cell-description', '<q-td :props="props">{{ props.value || "—" }}</q-td>')
        table.add_slot('no-data', '''
            <div class="groups-empty column items-center w-full">
                <q-icon name="groups" size="40px" />
                <div class="groups-empty-title">No groups found</div>
                <div>Create a group or try a different search.</div>
            </div>
        ''')
        table.add_slot('body-cell-actions', '''
            <q-td :props="props">
                <div class="group-row-actions">
                    <q-btn flat round icon="computer" :aria-label="'Assign computers to ' + props.row.name"
                        @click="$parent.$emit('assign', props.row)"><q-tooltip>Assign computers</q-tooltip></q-btn>
                    <q-btn flat round icon="edit" :aria-label="'Edit ' + props.row.name"
                        @click="$parent.$emit('edit', props.row)"><q-tooltip>Edit group</q-tooltip></q-btn>
                    <q-btn flat round icon="delete_outline" :aria-label="'Delete ' + props.row.name"
                        @click="$parent.$emit('delete_group', props.row)"><q-tooltip>Delete group</q-tooltip></q-btn>
                </div>
            </q-td>
        ''')

        async def refresh():
            if busy[0]:
                return
            busy[0] = True
            refresh_button.props('loading')
            table.props('loading')
            try:
                groups, computers = await run.io_bound(lambda: (list_groups(), list_computers()))
                table.rows = groups
                table.update()
                for value, count in zip(totals, [len(groups), len(computers)]):
                    value.set_text(str(count))
            except Exception:
                logging.getLogger(__name__).exception('Groups could not load')
                toast('Groups could not load. Please refresh and try again.', type='negative')
            finally:
                busy[0] = False
                refresh_button.props(remove='loading')
                table.props(remove='loading')

        editor = editor_dialog(current['id'], refresh)
        assign = assignment_dialog(current['id'], refresh)
        delete = delete_dialog(current['id'], refresh)
        def dispatch(e, action):
            group = next((g for g in table.rows if g['id'] == e.args.get('id')), None)
            return action(group) if group else None
        table.on('edit', lambda e: dispatch(e, editor))
        table.on('assign', lambda e: dispatch(e, assign))
        table.on('delete_group', lambda e: dispatch(e, delete))
        new_button.on_click(lambda: editor())
        refresh_button.on_click(refresh)
        import_tools(current['id'], refresh)
    ui.timer(0.01, refresh, once=True)
