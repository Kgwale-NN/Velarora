"""Schedule writes with atomic notification classes and optional group changes."""
from contextlib import nullcontext
from backend.db._core import _conn, _now
from backend.db.schedule_notifications import _replace_notify_classes, _invalidate_notify_cache

_UNSET = object()


def create_schedule(group_id, name, days_of_week, start_time, end_time, created_by=None,
                    model_id=None, use_custom_notify_classes=False, notify_class_ids=None,
                    is_active=True, *, _commit=True):
    """Create a weekly schedule and its notification classes in one transaction."""
    c = _conn()
    with c if _commit else nullcontext():
        cur = c.execute(
            'INSERT INTO schedule (group_id,name,days_of_week,start_time,end_time,model_id,'
            'use_custom_notify_classes,created_by,created_at,is_active) VALUES (?,?,?,?,?,?,?,?,?,?)',
            (group_id, name, days_of_week, start_time, end_time, model_id,
             int(bool(use_custom_notify_classes)), created_by, _now(), int(bool(is_active))))
        sid = cur.lastrowid
        _replace_notify_classes(c, sid, (notify_class_ids or []) if use_custom_notify_classes else [])
    if _commit:
        _invalidate_notify_cache()
    return sid


def update_schedule(schedule_id, name, days_of_week, start_time, end_time, is_active,
                    model_id=None, use_custom_notify_classes=False, notify_class_ids=None,
                    *, group_id=_UNSET, _commit=True):
    """Keep the group unchanged unless group_id is supplied, including explicit None."""
    c = _conn()
    with c if _commit else nullcontext():
        cur = c.execute(
            'UPDATE schedule SET name=?,days_of_week=?,start_time=?,end_time=?,is_active=?,'
            'model_id=?,use_custom_notify_classes=? WHERE id=?',
            (name, days_of_week, start_time, end_time, int(bool(is_active)), model_id,
             int(bool(use_custom_notify_classes)), schedule_id))
        if cur.rowcount == 0:
            raise ValueError('This schedule no longer exists. Refresh and try again.')
        if group_id is not _UNSET:
            c.execute('UPDATE schedule SET group_id=? WHERE id=?', (group_id, schedule_id))
        _replace_notify_classes(c, schedule_id, (notify_class_ids or []) if use_custom_notify_classes else [])
    if _commit:
        _invalidate_notify_cache()


def delete_schedule(schedule_id):
    with _conn() as c:
        c.execute('DELETE FROM schedule WHERE id=?', (schedule_id,))
    _invalidate_notify_cache()
