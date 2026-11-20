"""Run details operations."""
from __future__ import annotations
from backend.db._core import _conn
from backend.db.teacher_scope import require_run


def get_run_alerts(run_id: int) -> list[dict]:
    """
    Every notification fired during the run (prohibited-class detections),
    newest first, with class / computer / student resolved and a has_frame
    flag so the UI can offer a screenshot button per alert.
    """
    require_run(run_id)
    c = _conn()
    rows = c.execute("""
        SELECT n.id, n.event_id, n.created_at,
               COALESCE(dc.name, '?')                    AS class_name,
               COALESCE(dc.color_hex, '#888888')         AS class_color,
               comp.name                                 AS computer,
               COALESCE(u.username, e.os_username, '(unknown)') AS student,
               (e.frame_blob IS NOT NULL)                AS has_frame
        FROM notification n
        JOIN detection_event e       ON e.id  = n.event_id
        JOIN computer comp           ON comp.id = e.computer_id
        LEFT JOIN detection_class dc ON dc.id = n.class_id
        LEFT JOIN user u             ON u.id  = e.user_id
        WHERE e.run_id = ?
        ORDER BY n.created_at DESC, n.id DESC
    """, (run_id,)).fetchall()
    return [dict(r) for r in rows]


def get_run_detections(run_id: int) -> list[dict]:
    """
    Every individual detection of the run, newest first — the row set used
    for the CSV export.
    """
    require_run(run_id)
    c = _conn()
    rows = c.execute("""
        SELECT e.detected_at,
               comp.name                                         AS computer,
               COALESCE(u.username, e.os_username, '')           AS student,
               dc.name                                           AS class_name,
               d.confidence,
               d.box_x1, d.box_y1, d.box_x2, d.box_y2
        FROM detection d
        JOIN detection_event e  ON e.id  = d.event_id
        JOIN computer comp      ON comp.id = e.computer_id
        JOIN detection_class dc ON dc.id = d.class_id
        LEFT JOIN user u        ON u.id  = e.user_id
        WHERE e.run_id = ?
        ORDER BY e.detected_at DESC, d.id DESC
    """, (run_id,)).fetchall()
    return [dict(r) for r in rows]
