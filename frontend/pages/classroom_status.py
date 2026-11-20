"""Administrative live classroom overview without teacher impersonation or alarm-stop rights."""
from nicegui import ui
from backend.core.auth import require_auth,get_session_user
from backend.services.classroom_state import rooms,registry_lock
from frontend.pages._nav import nav
from frontend.pages.glass_fields import select_field
from frontend.pages.design_assets import stylesheet
from backend.db.group_queries import list_groups


@ui.page('/classroom-status')
def classroom_status():
    admin=require_auth('admin')
    if admin is None:return
    nav(admin);stylesheet('classrooms.css')
    with ui.column().classes('workstation-page w-full'):
        ui.label('Classroom overview').classes('text-3xl')
        selected=select_field('Classroom',{r['id']:r['name'] for r in list_groups()},value=None,icon='meeting_room')
        status=ui.label('Select a classroom.')
        grid=ui.element('div').classes('classroom-screen-grid w-full')
    key=[None];images={};sources={}
    def tick():
        user=get_session_user()
        if not user or user['id']!=admin['id'] or user['role']!='admin':grid.clear();return
        with registry_lock:room=rooms.get(selected.value)
        active=bool(room and room.monitor)
        status.set_text('Exam running · '+room.monitored_group_name if active else 'No exam running.')
        identity=id(room) if active else None
        if key[0]!=identity:
            grid.clear();images.clear();sources.clear();key[0]=identity
            if active:
                with grid:
                    for pc in room.computers:
                        with ui.card().classes('classroom-screen'):
                            ui.label(pc['name']);images[pc['name']]=ui.image('').props('fit=contain no-spinner')
        if active:
            for name,image in images.items():
                frame=room.latest_frames.get(name)
                if frame and frame[0]!=sources.get(name):image.set_source(frame[0]);sources[name]=frame[0]
    ui.timer(.5,tick)
