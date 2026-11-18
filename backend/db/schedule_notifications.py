"""Atomic replacement of a schedule's notification class selection."""
from backend.db._core import _conn


def get_notify_class_ids_for_schedule(schedule_id: int) -> list[int]:
    return [r[0] for r in _conn().execute(
        'SELECT class_id FROM schedule_notification_class WHERE schedule_id=?', (schedule_id,))]


def _replace_notify_classes(c, schedule_id, class_ids):
    c.execute('DELETE FROM schedule_notification_class WHERE schedule_id=?', (schedule_id,))
    c.executemany('INSERT INTO schedule_notification_class(schedule_id,class_id) VALUES (?,?)',
                  [(schedule_id, cid) for cid in sorted(set(class_ids))])


def _invalidate_notify_cache():
    try:
        from backend.services.alert_service import invalidate_prohibited_cache
        invalidate_prohibited_cache()
    except Exception:
        pass


def set_schedule_notify_classes(schedule_id: int, class_ids: list[int]) -> None:
    with _conn() as c:
        _replace_notify_classes(c, schedule_id, class_ids)
    _invalidate_notify_cache()
