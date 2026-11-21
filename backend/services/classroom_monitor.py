"""Atomic classroom claims shared by teacher controls and the scheduler."""
from backend.services.classroom_state import ClassroomState, rooms, registry_lock
from backend.db._core import _conn
from backend.db.user_queries import get_user_by_id
from backend.db.group_queries import list_computers_in_group
from backend.db.database import get_active_model, get_model_by_id, log_action


def start_classroom(room_id,owner_id,schedule_id=None,controller_factory=None):
    teacher=get_user_by_id(owner_id)
    if not teacher or not teacher['is_active'] or teacher['role']!='teacher':
        raise PermissionError('An active teacher account is required.')
    from backend.config import collect_cfg
    import os
    if os.environ.get("VELARORA_CLOUD_DEMO") == "true":
        raise ValueError("Windows classroom capture is unavailable in the cloud demo. Browser screen sharing must be used instead.")
    from backend.services.monitor_service import MonitorController
    cfg=collect_cfg()
    if cfg.get("auth_method","key")=="key" and not cfg.get("key_data"):
        raise ValueError("Veyon authentication key is missing. Ask your administrator to check Settings.")
    model=get_active_model()
    if schedule_id:
        schedule=_conn().execute('SELECT * FROM schedule WHERE id=? AND created_by=? AND group_id=?',(schedule_id,owner_id,room_id)).fetchone()
        if not schedule:
            raise PermissionError('This schedule is not yours or belongs to another classroom.')
        if schedule['model_id']:
            model=get_model_by_id(schedule['model_id'])
    if not model:
        raise ValueError('An administrator must activate a model first.')
    model_path=model.get('onnx_path') or model.get('pt_path')
    if model_path:
        cfg['model_path']=model_path
    cfg['detect_imgsz']=model.get('imgsz') or cfg['detect_imgsz']
    rows=list_computers_in_group(room_id)
    if not rows:
        raise ValueError('This classroom has no registered computers. Ask your administrator.')
    group=_conn().execute('SELECT name FROM computer_group WHERE id=?',(room_id,)).fetchone()
    computers=[{'name':r['name'],'host':r['host_address']} for r in rows]
    with registry_lock:
        old=rooms.get(room_id)
        if old and (old.monitor or old.stopping):
            raise ValueError('Another exam is already running in this classroom. Its teacher must end it first.')
        wanted={r['id'] for r in rows}
        placeholders=','.join('?' for _ in wanted)
        pending=_conn().execute(f'SELECT 1 FROM workstation_alarm a LEFT JOIN computer_agent ca ON ca.computer_id=a.computer_id '
            f'WHERE a.computer_id IN ({placeholders}) AND (a.stopped_at IS NULL OR ca.audio_active=1) LIMIT 1',list(wanted)).fetchone()
        if pending:
            raise ValueError('A previous exam has an active or unacknowledged alarm on a classroom PC. Its teacher must stop it before a new exam starts.')
        hosts={pc['host'].lower() for pc in computers}
        if any((room.monitor or room.stopping) and (wanted.intersection(room.computer_ids.values()) or hosts.intersection(pc['host'].lower() for pc in room.computers)) for room in rooms.values()):
            raise ValueError('A classroom computer is already being monitored in another exam.')
        room=ClassroomState(room_id,owner_id)
        room.computer_ids={r['name']:r['id'] for r in rows}
        room.computers=computers
        room.monitored_group_name=group['name']
        room.schedule_triggered=bool(schedule_id)
        room.schedule_id=schedule_id
        factory=controller_factory or MonitorController
        room.monitor=factory(cfg,computers=computers,model_id=model['id'],schedule_id=schedule_id,
            started_by=owner_id,group_name=group['name'],workspace=room)
        rooms[room_id]=room
        room.monitor.start()
        log_action('classroom.exam_start',user_id=owner_id,entity='computer_group',entity_id=room_id)
        return room


def stop_classroom(room_id,owner_id,manual=True):
    # Reserve the room, then release the registry while waiting for network/model threads.
    with registry_lock:
        room=rooms.get(room_id)
        if not room or room.owner_id!=owner_id:
            raise PermissionError('Only the teacher running this classroom can end its exam.')
        if room.stopping:
            raise ValueError('This exam is already stopping. Please wait.')
        room.stopping=True
        monitor=room.monitor
    try:
        if monitor:
            monitor.stop()
    finally:
        with registry_lock:
            room.monitor=None
            room.stopping=False
            if manual:
                room.suppressed_schedule=room.schedule_id
            room.schedule_triggered=False
            room.latest_frames.clear()
    log_action('classroom.exam_stop',user_id=owner_id,entity='computer_group',entity_id=room_id)
