"""Evaluate each classroom independently; scheduled exams retain their creator's ownership."""
import logging
import threading
import time
from backend.services.classroom_state import rooms,registry_lock
from backend.services.classroom_monitor import start_classroom,stop_classroom

log=logging.getLogger(__name__)
TICK_SECONDS=5


def _tick():
    from backend.db.schedule_timing import get_active_schedules_now
    active=get_active_schedules_now()
    by_room={}
    for schedule in sorted(active,key=lambda s:s['id']):
        if schedule.get('group_id') and schedule.get('created_by'):
            by_room.setdefault(schedule['group_id'],schedule)
    active_ids={s['id'] for s in active}
    with registry_lock:existing=list(rooms.items())
    for gid,room in existing:
        if room.suppressed_schedule not in active_ids:
            room.suppressed_schedule=None
        if room.monitor and room.schedule_triggered and room.schedule_id not in active_ids:
            stop_classroom(gid,room.owner_id,manual=False)
    for gid,schedule in by_room.items():
        with registry_lock:room=rooms.get(gid)
        if room and (room.monitor or room.stopping or room.suppressed_schedule==schedule['id']):
            continue
        try:start_classroom(gid,schedule['created_by'],schedule['id'])
        except Exception as exc:log.warning('Classroom %s schedule could not start: %s',gid,exc)


def _loop():
    while True:
        try:_tick()
        except Exception:log.exception('Schedule evaluation failed')
        time.sleep(TICK_SECONDS)


def start_scheduler():
    worker=threading.Thread(target=_loop,daemon=True,name='classroom-scheduler')
    worker.start();return worker
