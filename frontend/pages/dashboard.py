"""Teacher classroom screen grid: live data is available only for this teacher's exams."""
from nicegui import app,run,ui
from fastapi import Request
from backend.core.auth import require_auth
from backend.db.group_queries import list_groups
from backend.services.classroom_state import current_room,rooms,registry_lock
from backend.services.classroom_monitor import start_classroom,stop_classroom
from frontend.pages._nav import nav
from frontend.pages._snapshot import make_snapshot_dialogs
from frontend.pages.admin_shell import toast
from frontend.pages.design_assets import stylesheet
from frontend.pages.glass_fields import select_field
from frontend.pages.classroom_tools import alarm_controls


@ui.page('/')
def page_dashboard(request:Request):
    # A bookmarked big-screen URL restores the room even after the browser is closed.
    room_hint=request.query_params.get('classroom','')
    if room_hint.isdigit() and len(room_hint)<10:
        app.storage.user['classroom_id']=int(room_hint)
    current=require_auth('teacher')
    if current is None:return
    from frontend.pages.teacher_calls import bind
    launch_exam=bind(current['id'],start_classroom)
    finish_exam=bind(current['id'],stop_classroom)
    nav(current)
    stylesheet('teacher-dashboard.css');stylesheet('classrooms.css')
    _,_,show_snapshot=make_snapshot_dialogs()
    with ui.column().classes('teacher-dashboard w-full'):
        ui.label('Your classroom, at a glance.').classes('dashboard-title')
        ui.label('Choose this big screen’s classroom. Your exam records stay with your account.').classes('dashboard-subtitle')
        with ui.card().classes('dashboard-controls w-full'):
            groups={r['id']:r['name'] for r in list_groups()}
            saved=app.storage.user.get('classroom_id')
            if saved not in groups:saved=None
            with ui.row().classes('w-full items-end gap-4'):
                room_select=select_field('This classroom',groups,value=saved,icon='meeting_room')
                status=ui.label('Choose a classroom').classes('dashboard-status')
                start=ui.button('Start exam',icon='play_arrow').props('no-caps')
                stop=ui.button('End exam',icon='stop').props('outline no-caps')
            if not groups:ui.label('An administrator must add classrooms and their PCs under Classrooms first.')
        ui.label('Active alarms').classes('dashboard-section-title')
        alarm_controls(current['id'])
        with ui.row().classes('w-full items-center justify-between'):
            ui.label('Classroom screens').classes('dashboard-section-title')
            annotations=ui.switch('Annotations',value=True).props('color=white')
        empty=ui.label('Start an exam to see your classroom screens.').classes('dashboard-subtitle')
        grid=ui.element('div').classes('classroom-screen-grid w-full')
        with ui.card().classes('dashboard-controls w-full'):
            ui.label('Your exam activity').classes('dashboard-section-title')
            logs=ui.textarea(value='').props('readonly outlined rows=6').classes('dashboard-log w-full')
    cards={};sources={};room_key=[None];log_seq=[-1];busy=[False]
    def choose():
        app.storage.user['classroom_id']=room_select.value
        cards.clear();sources.clear();grid.clear();room_key[0]=None
        logs.set_value('');log_seq[0]=-1
        tick()
    room_select.on_value_change(choose)
    async def launch():
        if busy[0]:return
        if not room_select.value:
            toast('Choose a classroom first.',type='warning');return
        busy[0]=True;start.props('loading')
        try:
            await run.io_bound(launch_exam,room_select.value,current['id'])
        except Exception as exc:toast(str(exc),type='negative')
        finally:busy[0]=False;start.props(remove='loading');tick()
    async def finish():
        if busy[0]:return
        busy[0]=True;stop.props('loading')
        try:await run.io_bound(finish_exam,room_select.value,current['id'])
        except Exception as exc:toast(str(exc),type='negative')
        finally:busy[0]=False;stop.props(remove='loading');tick()
    start.on_click(launch);stop.on_click(finish)
    def view(name):
        room=current_room(room_select.value,current['id'])
        if room and room.monitor and name in room.latest_frames:
            ann,raw,_=room.latest_frames[name]
            show_snapshot(raw,groups.get(room_select.value,'')+' · '+name,ann)
    def tick():
        from backend.core.auth import get_session_user
        signed=get_session_user()
        if not signed or signed["id"]!=current["id"]:
            grid.clear();logs.set_value("");start.disable();stop.disable();return
        gid=room_select.value
        with registry_lock:occupied=rooms.get(gid)
        room=current_room(gid,current['id'])
        running=bool(room and room.monitor)
        other=bool(occupied and occupied.monitor and occupied.owner_id!=current['id'])
        status.set_text('Another teacher is running an exam here' if other else 'Exam running' if running else 'Exam stopped' if gid else 'Choose a classroom')
        start.set_enabled(bool(gid) and not running and not other and not busy[0]);stop.set_enabled(running and not busy[0])
        identity=id(room) if running else None
        if identity!=room_key[0]:
            grid.clear();cards.clear();sources.clear();room_key[0]=identity
            if running:
                with grid:
                    for pc in room.computers:
                        name=pc['name']
                        with ui.card().classes('classroom-screen'):
                            ui.label(name).classes('dashboard-section-title')
                            image=ui.image('').props('fit=contain no-spinner').classes('classroom-screen-image')
                            image.on('click',lambda n=name:view(n))
                            detail=ui.label('Waiting for a screen').classes('text-sm text-gray-400')
                            cards[name]=(image,detail)
        empty.set_visibility(not running)
        if not room:
            logs.set_value('');return
        if room.log_total!=log_seq[0]:
            log_seq[0]=room.log_total;logs.set_value('\n'.join(reversed(room.log_buffer[-100:])))
        for name,(image,detail) in cards.items():
            frame=room.latest_frames.get(name)
            if not frame:continue
            ann,raw,dets=frame;src=ann if annotations.value else raw
            if sources.get(name)!=src:image.set_source(src);sources[name]=src
            detail.set_text(('Online' if room.is_computer_online(name) else 'Offline')+' · '+(', '.join(d['class_name'] for d in dets) or 'No model detections'))
    tick();ui.timer(.5,tick)
