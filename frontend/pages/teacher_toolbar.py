"""Header controls act only on the selected classroom and authenticated teacher."""
from nicegui import app,run,ui
from backend.services.classroom_state import current_room
from backend.services.classroom_monitor import start_classroom,stop_classroom
from frontend.pages.admin_shell import toast


def monitoring_controls(current_user):
    from frontend.pages.teacher_calls import bind
    launch_exam=bind(current_user['id'],start_classroom)
    finish_exam=bind(current_user['id'],stop_classroom)
    status=ui.label('').classes('teacher-monitor-status text-xs')
    async def start():
        gid=app.storage.user.get('classroom_id')
        if not gid:toast('Choose your classroom on Dashboard first.',type='warning');return
        try:await run.io_bound(launch_exam,gid,current_user['id'])
        except Exception as exc:toast(str(exc),type='negative')
    async def stop():
        try:await run.io_bound(finish_exam,app.storage.user.get('classroom_id'),current_user['id'])
        except Exception as exc:toast(str(exc),type='negative')
    play=ui.button('Start',icon='play_arrow',on_click=start).props('no-caps aria-label="Start monitoring"').classes('teacher-header-start')
    end=ui.button('Stop',icon='stop',on_click=stop).props('no-caps aria-label="Stop monitoring"').classes('teacher-header-stop')
    def sync():
        room=current_room(app.storage.user.get('classroom_id'),current_user['id'])
        running=bool(room and room.monitor)
        status.set_text(('Running · '+room.monitored_group_name) if running else 'Stopped')
        play.set_enabled(not running);end.set_enabled(running)
    sync();ui.timer(1,sync)
