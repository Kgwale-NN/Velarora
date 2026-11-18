"""Validate and save an editor submission and audit record in one transaction."""
import re
from backend.db._core import _conn
from backend.db.audit import _insert_audit
from backend.db.schedule_updates import create_schedule, update_schedule
from backend.db.schedule_timing import find_overlapping_schedules
from backend.db.schedule_notifications import _invalidate_notify_cache


def save_editor_schedule(payload, user_id, schedule_id=None):
    name = (payload.get('name') or '').strip()
    if not name:
        raise ValueError('Name is required.')
    days = sorted(set(str(d) for d in payload.get('days', [])))
    if not days or any(d not in '0123456' or len(d) != 1 for d in days):
        raise ValueError('Select at least one valid day.')
    start, end = payload.get('start') or '', payload.get('end') or ''
    pattern = r'(?:[01]\d|2[0-3]):[0-5]\d'
    if not re.fullmatch(pattern, start) or not re.fullmatch(pattern, end):
        raise ValueError('Set valid start and end times in HH:MM format.')
    if start >= end:
        raise ValueError('End time must be after start time on the same day.')
    gid, mid = payload.get('group_id'), payload.get('model_id')
    custom = bool(payload.get('custom'))
    selected = set(payload.get('notify_ids', [])) if custom else set()
    c = _conn()
    with c:
        c.execute('BEGIN IMMEDIATE')
        if gid is not None and not c.execute('SELECT 1 FROM computer_group WHERE id=?', (gid,)).fetchone():
            raise ValueError('The selected group no longer exists. Reopen this window.')
        if mid is not None and not c.execute('SELECT 1 FROM ml_model WHERE id=?', (mid,)).fetchone():
            raise ValueError('The selected model no longer exists. Reopen this window.')
        resolved_mid = mid
        if mid is None:
            active = c.execute('SELECT id FROM ml_model WHERE is_active=1 LIMIT 1').fetchone()
            resolved_mid = active[0] if active else None
        valid_ids = {r[0] for r in c.execute('SELECT class_id FROM model_class WHERE model_id=?', (resolved_mid,))}
        if not selected.issubset(valid_ids):
            raise ValueError('The model or its classes changed. Reopen this window and review the alert rules.')
        day_string = ','.join(days)
        conflicts = find_overlapping_schedules(day_string, start, end, exclude_id=schedule_id)
        if conflicts:
            raise ValueError('Time conflict with ' + ', '.join(s['name'] for s in conflicts) + '. Choose another time or day.')
        kwargs = dict(model_id=mid, use_custom_notify_classes=custom, notify_class_ids=list(selected), _commit=False)
        if schedule_id is None:
            sid = create_schedule(gid, name, day_string, start, end, created_by=user_id,
                                  is_active=bool(payload.get('active', True)), **kwargs)
            action = 'schedule.create'
        else:
            sid = schedule_id
            update_schedule(sid, name, day_string, start, end, bool(payload.get('active', True)), group_id=gid, **kwargs)
            action = 'schedule.update'
        _insert_audit(c, action, user_id=user_id, entity='schedule', entity_id=sid,
                      detail=f'name={name}, days={day_string}, {start}-{end}')
    _invalidate_notify_cache()
    return sid
