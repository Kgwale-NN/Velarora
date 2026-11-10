"""Schedule updates operations."""
from __future__ import annotations
from typing import Optional
from backend.db._core import _conn, _now
from backend.db.schedule_notifications import set_schedule_notify_classes


def create_schedule(
    group_id:                  int,
    name:                      str,
    days_of_week:              str,
    start_time:                str,
    end_time:                  str,
    created_by:                Optional[int]       = None,
    model_id:                  Optional[int]       = None,
    use_custom_notify_classes: bool                = False,
    notify_class_ids:          Optional[list[int]] = None,
) -> int:
    c = _conn()
    cur = c.execute(
        "INSERT INTO schedule "
        "(group_id, name, days_of_week, start_time, end_time, "
        " model_id, use_custom_notify_classes, created_by, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (group_id, name, days_of_week, start_time, end_time,
         model_id, 1 if use_custom_notify_classes else 0,
         created_by, _now()),
    )
    c.commit()
    sid = cur.lastrowid
    if use_custom_notify_classes and notify_class_ids:
        set_schedule_notify_classes(sid, notify_class_ids)
    return sid


def update_schedule(
    schedule_id:               int,
    name:                      str,
    days_of_week:              str,
    start_time:                str,
    end_time:                  str,
    is_active:                 bool,
    model_id:                  Optional[int]       = None,
    use_custom_notify_classes: bool                = False,
    notify_class_ids:          Optional[list[int]] = None,
) -> None:
    c = _conn()
    c.execute(
        "UPDATE schedule SET name=?, days_of_week=?, start_time=?, "
        "end_time=?, is_active=?, model_id=?, use_custom_notify_classes=? "
        "WHERE id=?",
        (name, days_of_week, start_time, end_time,
         1 if is_active else 0,
         model_id, 1 if use_custom_notify_classes else 0,
         schedule_id),
    )
    c.commit()
    set_schedule_notify_classes(
        schedule_id,
        notify_class_ids if (use_custom_notify_classes and notify_class_ids is not None) else [],
    )


def delete_schedule(schedule_id: int) -> None:
    c = _conn()
    c.execute("DELETE FROM schedule WHERE id = ?", (schedule_id,))
    c.commit()
