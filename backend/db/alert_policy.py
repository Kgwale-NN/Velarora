"""Alert policy operations."""
from __future__ import annotations
from typing import Optional
from backend.db._core import _conn


def get_prohibited_class_ids(
    model_id:    Optional[int],
    schedule_id: Optional[int] = None,
) -> dict[int, dict]:
    """
    Return {class_index: {"id": db_id, "color_hex": str}} for all alert-enabled
    classes scoped to the given model.

    When schedule_id is provided and that schedule has use_custom_notify_classes=1,
    the class set comes from schedule_notification_class instead of
    detection_class.notification_enabled (global setting).

    Returns an empty dict when model_id is None (no active model → no alerts).
    """
    if model_id is None:
        return {}
    c = _conn()

    # Determine whether to use per-schedule class set
    use_custom = False
    if schedule_id is not None:
        row = c.execute(
            "SELECT use_custom_notify_classes FROM schedule WHERE id = ?",
            (schedule_id,),
        ).fetchone()
        use_custom = bool(row and row[0])

    if use_custom:
        rows = c.execute("""
            SELECT mc.class_index, dc.id, dc.color_hex
            FROM   schedule_notification_class snc
            JOIN   detection_class dc ON dc.id = snc.class_id
            JOIN   model_class mc     ON mc.class_id = dc.id
            WHERE  snc.schedule_id = ?
              AND  mc.model_id = ?
        """, (schedule_id, model_id)).fetchall()
    else:
        rows = c.execute("""
            SELECT mc.class_index, dc.id, dc.color_hex
            FROM   detection_class dc
            JOIN   model_class mc ON mc.class_id = dc.id
            WHERE  dc.notification_enabled = 1
              AND  mc.model_id = ?
        """, (model_id,)).fetchall()

    return {r[0]: {"id": r[1], "color_hex": r[2]} for r in rows}
