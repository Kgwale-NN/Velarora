"""Schedule queries operations."""
from __future__ import annotations
from typing import Optional
from backend.db._core import _conn
from backend.db.teacher_scope import owner_id, require_schedule
from backend.db.schedule_notifications import get_notify_class_ids_for_schedule


def list_schedules() -> list[dict]:
    c = _conn()
    rows = c.execute("""
        SELECT s.*,
               g.name AS group_name,
               m.name AS model_name,
               (SELECT COUNT(*) FROM schedule_notification_class snc
                WHERE snc.schedule_id = s.id) AS notify_class_count,
               (SELECT GROUP_CONCAT(dc.name, '||')
                FROM   schedule_notification_class snc
                JOIN   detection_class dc ON dc.id = snc.class_id
                WHERE  snc.schedule_id = s.id) AS notify_class_names
        FROM   schedule s
        LEFT JOIN computer_group g ON g.id = s.group_id
        LEFT JOIN ml_model       m ON m.id = s.model_id
        WHERE (? IS NULL OR s.created_by=?)
        ORDER BY g.name, s.start_time
    """,(owner_id(),owner_id())).fetchall()
    return [dict(r) for r in rows]


def list_schedules_for_group(group_id: int) -> list[dict]:
    c = _conn()
    rows = c.execute(
        "SELECT * FROM schedule WHERE group_id = ? ORDER BY start_time",
        (group_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_schedule(schedule_id: int) -> Optional[dict]:
    c = _conn()
    require_schedule(schedule_id)
    row = c.execute("""
        SELECT s.*,
               g.name AS group_name,
               m.name AS model_name
        FROM   schedule s
        LEFT JOIN computer_group g ON g.id = s.group_id
        LEFT JOIN ml_model       m ON m.id = s.model_id
        WHERE  s.id = ?
    """, (schedule_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["notify_class_ids"] = get_notify_class_ids_for_schedule(schedule_id)
    return d


def list_schedules_using_model(model_id: int) -> list[dict]:
    """Return all schedules whose model_id matches — used before model deletion."""
    c = _conn()
    rows = c.execute(
        "SELECT s.*, g.name AS group_name "
        "FROM schedule s "
        "LEFT JOIN computer_group g ON g.id = s.group_id "
        "WHERE s.model_id = ?",
        (model_id,),
    ).fetchall()
    return [dict(r) for r in rows]
