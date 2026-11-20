"""Administrator workstation provisioning; secrets are delivered once, never stored in plain text."""
import json
from nicegui import run,ui
from backend.core.auth import require_auth
from backend.db.computers import list_computers
from backend.db.agent_credentials import provision_agent
from backend.db._core import _conn
from frontend.pages._nav import nav
from frontend.pages.glass_fields import select_field,text_field
from frontend.pages.admin_shell import toast
from frontend.pages.design_assets import stylesheet


@ui.page('/workstations')
def workstations():
    admin=require_auth('admin')
    if admin is None:return
    nav(admin);stylesheet('classrooms.css')
    with ui.column().classes('workstation-page w-full'):
        ui.label('Workstation setup').classes('text-3xl')
        ui.label('Register PCs under Classrooms, then install the Windows agent on each student PC. Veyon captures screens; the agent reports app names and plays the local alarm.')
        with ui.card():
            choices={r['id']:r['name'] for r in list_computers()}
            pc=select_field('Computer',choices,value=None,icon='computer')
            url=text_field('Server URL',icon='link',value=str(ui.context.client.request.base_url).rstrip('/'),placeholder='https://school-server:8080')
            ui.label('Use an HTTPS address reachable from the student PCs. localhost works only when testing the server PC itself.').classes('text-gray-400')
            ui.label('Creating a new configuration revokes this PC’s previous agent key. Keep the downloaded file on that PC only.').classes('text-gray-400')
            error=ui.label('').props('role=alert')
            async def download():
                signed=require_auth("admin")
                if not signed or signed["id"]!=admin["id"]:
                    return
                from urllib.parse import urlparse
                parsed=urlparse(url.value)
                if not pc.value or parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
                    error.set_text('Choose a PC and enter a plain server URL.');return
                if parsed.scheme!='https' and parsed.hostname not in ('127.0.0.1','localhost','::1'):
                    error.set_text('Use HTTPS for classroom-network connections.');return
                button.props('loading')
                try:
                    token=await run.io_bound(provision_agent,admin['id'],pc.value)
                    content=json.dumps({'server_url':url.value.rstrip('/'),'token':token},indent=2).encode()
                    ui.download(content,filename=f'velarora-pc-{pc.value}.json',media_type='application/json')
                    error.set_text('');toast('Configuration downloaded. Install it on the selected workstation.',type='positive')
                except Exception as exc:error.set_text(str(exc))
                finally:button.props(remove='loading')
            button=ui.button('Download agent configuration',icon='download',on_click=download).props('no-caps')
        with ui.card():
            ui.label('Big-screen classroom links').classes('text-xl')
            ui.label('Bookmark the right link on each classroom big screen. It restores that room before teacher sign-in.')
            from backend.db.group_queries import list_groups
            base=str(ui.context.client.request.base_url).rstrip('/')
            for group in list_groups():
                ui.link(group['name'],f"{base}/?classroom={group['id']}")
        with ui.card():
            ui.label('Agent connections').classes('text-xl')
            rows=[dict(r) for r in _conn().execute('SELECT c.name,ca.last_seen,ca.last_app,ca.enabled FROM computer_agent ca JOIN computer c ON c.id=ca.computer_id ORDER BY c.name')]
            ui.table(columns=[{'name':key,'label':label,'field':key,'align':'left'} for key,label in [('name','Computer'),('last_seen','Last connected'),('last_app','Foreground app'),('enabled','Enabled')]],rows=rows,row_key='name').classes('w-full')
            ui.button('Refresh',icon='refresh',on_click=ui.navigate.reload).props('flat no-caps')
