"""Teacher-owned Windows application policies, applied only during their exams."""
from nicegui import run,ui
from backend.core.auth import require_auth
from backend.db.application_policy import get_policy,save_policy
from frontend.pages._nav import nav
from frontend.pages.glass_fields import select_field
from frontend.pages.admin_shell import toast
from frontend.pages.design_assets import stylesheet


@ui.page('/alerts')
async def app_rules():
    teacher=require_auth('teacher')
    if teacher is None:return
    nav(teacher);stylesheet('classrooms.css')
    from frontend.pages.teacher_calls import bind
    load_rules=bind(teacher['id'],get_policy)
    save_rules=bind(teacher['id'],save_policy)
    policy=await run.io_bound(load_rules,teacher['id'])
    with ui.column().classes('workstation-page w-full'):
        ui.label('Your app rules').classes('text-3xl')
        ui.label('These rules apply to your exams in every classroom. They use the foreground Windows executable name.')
        with ui.card():
            mode=select_field('Policy',{'blocklist':'Block listed apps','allowlist':'Allow only listed apps'},value=policy['mode'],icon='policy')
            processes=ui.textarea('Executable names — one per line',value='\n'.join(policy['processes']),placeholder='chatgpt.exe\nnotepad.exe').props('outlined rows=8').classes('w-full')
            ui.label('Allow-only mode alarms on any foreground executable missing from this list. Include your exam browser and other permitted tools.').classes('text-gray-400')
            error=ui.label('').props('role=alert')
            async def save():
                button.props('loading')
                try:
                    await run.io_bound(save_rules,teacher['id'],mode.value,processes.value.splitlines())
                    error.set_text('');toast('Your app rules were saved.',type='positive')
                except Exception as exc:error.set_text(str(exc))
                finally:button.props(remove='loading')
            button=ui.button('Save app rules',icon='check',on_click=save).props('no-caps')
        ui.label('Websites inside Chrome share chrome.exe. Use screenshot-model rules in an exam schedule to detect a specific website such as ChatGPT.').classes('text-gray-400')
