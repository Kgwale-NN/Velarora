"""Shared classroom selector and teacher-only alarm controls."""
from nicegui import app,run,ui
from backend.db.workstation_alarms import list_alarms,stop_alarm
from frontend.pages.admin_shell import toast


def selected_classroom():
    return app.storage.user.get('classroom_id')


def alarm_controls(teacher_id):
    from frontend.pages.teacher_calls import bind
    alarms=bind(teacher_id,list_alarms)
    stop=bind(teacher_id,stop_alarm)
    container=ui.column().classes('classroom-alarm-list w-full')
    signature=[None]
    busy=[False]
    async def silence(alarm_id):
        with container:
            try:
                await run.io_bound(stop,teacher_id,alarm_id)
                toast('Stop command saved. The workstation will silence when it next connects.',type='positive')
                await refresh()
            except Exception as exc:
                toast(str(exc),type='negative')
    async def refresh():
        if busy[0]:return
        busy[0]=True
        try:
            rows=await run.io_bound(alarms,teacher_id)
            value=[(r['id'],r['last_seen'],r['stopped_at'],r['audio_active']) for r in rows]
            if value==signature[0]:return
            signature[0]=value
            container.clear()
            with container:
                if not rows:
                    ui.label('No active alarms in your exams.').classes('text-gray-400')
                for alarm in rows:
                    with ui.card().classes('classroom-alarm w-full'):
                        with ui.row().classes('w-full items-center justify-between'):
                            ui.icon('notifications_active')
                            ui.label(f"{alarm['classroom'] or 'Classroom'} · {alarm['computer']} opened {alarm['app_name']}").classes('flex-1')
                            if alarm['stopped_at']:
                                ui.label('Stop requested — waiting for workstation').classes('text-sm text-gray-300')
                            else:
                                ui.button('Stop alarm',icon='volume_off',on_click=lambda a=alarm:silence(a['id'])).props('no-caps')
                        if not alarm['stopped_at']:
                            ui.label('Agent reports siren running' if alarm['audio_active'] else 'Waiting for workstation to start the siren').classes('text-sm text-gray-300')
                        ui.label('Workstation last connected: '+(alarm['last_seen'] or 'Agent has not connected')).classes('text-sm text-gray-400')
        except Exception:
            with container:toast('Alarm status could not be refreshed.',type='negative')
        finally:busy[0]=False
    ui.timer(.05,refresh,once=True);ui.timer(2,refresh)
    return container
