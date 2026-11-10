"""Schedule notifications operations."""
from __future__ import annotations
from backend.db._core import _conn


def get_notify_class_ids_for_schedule(schedule_id: int) -> list[int]:
    """Return the list of detection_class IDs configured for this schedule."""
    c = _conn()
    rows = c.execute(
        "SELECT class_id FROM schedule_notification_class WHERE schedule_id = ?",
        (schedule_id,),
    ).fetchall()
    return [r[0] for r in rows]


def set_schedule_notify_classes(schedule_id: int, class_ids: list[int]) -> None:
    """Replace the full set of per-schedule notification classes atomically."""
    c = _conn()
    c.execute(
        "DELETE FROM schedule_notification_class WHERE schedule_id = ?",
        (schedule_id,),
    )
    if class_ids:
        c.executemany(
            "INSERT INTO schedule_notification_class (schedule_id, class_id) VALUES (?, ?)",
            [(schedule_id, cid) for cid in class_ids],
        )
    c.commit()
    try:
        from backend.services.alert_service import invalidate_prohibited_cache
        invalidate_prohibited_cache()
    except Exception:
        pass
