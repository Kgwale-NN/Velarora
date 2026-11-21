"""Optional Veyon import and configuration tools, kept off the UI thread."""
import json
import logging
import subprocess
from nicegui import run, ui
from backend.config import get_settings
from backend.services.classroom_import import import_locations as _import_locations
from frontend.pages.admin_shell import toast
from frontend.pages.group_dialogs import _frame
from frontend.translate import t



def _raw_config(cli):
    result = subprocess.run([cli, 'config', 'get', 'BuiltinDirectory/NetworkObjects'],
                            capture_output=True, text=True, timeout=10)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or 'Veyon could not read its configuration.')
    raw = result.stdout.strip()
    if not raw.startswith(('{', '[')) and '=' in raw:
        raw = raw.split('=', 1)[1].strip()
    try:
        return json.dumps(json.loads(raw), indent=2)
    except ValueError:
        return raw or '(empty)'


def import_tools(user_id, refresh):
    dialog, _, body, footer = _frame('Veyon configuration', 'group-config-dialog')
    with body:
        raw_area = ui.textarea().props('outlined readonly rows=16 aria-label="Veyon configuration"').classes('group-config-text w-full')
    with footer:
        ui.button('Close', on_click=dialog.close).props('flat no-caps')
    with ui.expansion('Import from Veyon', icon='download').classes('group-import-panel w-full'):
        ui.label('Bring your existing Veyon locations and computers into Groups.').classes('groups-help')
        with ui.row().classes('group-import-actions w-full gap-3'):
            raw_button = ui.button('View configuration', icon='code').props('outline no-caps')
            import_button = ui.button('Import locations', icon='download').props('no-caps')

    async def execute(button, import_mode):
        if button.props.get('loading'):
            return
        button.props('loading')
        cli = ''
        try:
            cfg = await run.io_bound(get_settings)
            cli = cfg.get('veyon_cli', '')
            if not cli:
                toast(t('groups_veyon_cli_missing'), type='warning')
                return
            if import_mode:
                n_groups, n_comps = await run.io_bound(_import_locations, cli, user_id)
                if not n_groups:
                    toast(t('groups_no_veyon_comps'), type='warning')
                    return
                toast(t('groups_imported').format(n_groups=n_groups, n_comps=n_comps), type='positive')
                await refresh()
            else:
                raw_area.set_value(await run.io_bound(_raw_config, cli))
                dialog.open()
        except FileNotFoundError:
            toast(t('groups_veyon_not_found').format(path=cli), type='negative')
        except subprocess.TimeoutExpired:
            toast(t('groups_veyon_timeout'), type='warning')
        except Exception:
            logging.getLogger(__name__).exception('Veyon group tool failed')
            toast('Veyon could not complete this request. Check its configuration and try again.', type='negative')
        finally:
            button.props(remove='loading')

    raw_button.on_click(lambda: execute(raw_button, False))
    import_button.on_click(lambda: execute(import_button, True))
