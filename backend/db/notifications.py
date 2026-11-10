"""Notifications operations."""
from __future__ import annotations
from backend.db._core import _conn, _now


def insert_notification(event_id: int, class_id: int, _commit: bool = True) -> int:
    c = _conn()
    cur = c.execute(
        "INSERT INTO notification (event_id, class_id, created_at) "
        "VALUES (?, ?, ?)",
        (event_id, class_id, _now()),
    )
    if _commit:
        c.commit()
    return cur.lastrowid


def list_notifications(limit: int = 60) -> list[dict]:
    """
    Returns rows with class_name, class_color, computer, and student resolved
    via JOINs so callers get a complete picture without stored duplicates.
    """
    c = _conn()
    rows = c.execute("""
        SELECT
            n.id, n.event_id, n.class_id,
            COALESCE(dc.name,      '(unknown)') AS class_name,
            COALESCE(dc.color_hex, '#888888')   AS class_color,
            COALESCE(comp.name,    '(unknown)')  AS computer,
            COALESCE(u.username, e.os_username, '(unknown)') AS student,
            n.is_read, n.created_at,
            CASE WHEN e.frame_blob IS NOT NULL THEN 1 ELSE 0 END AS has_frame
        FROM notification n
        LEFT JOIN detection_class dc ON dc.id = n.class_id
        LEFT JOIN detection_event e  ON e.id  = n.event_id
        LEFT JOIN computer comp      ON comp.id = e.computer_id
        LEFT JOIN user u             ON u.id    = e.user_id
        ORDER BY n.created_at DESC
        LIMIT ?
    """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def count_unread_notifications() -> int:
    c = _conn()
    return c.execute(
        "SELECT COUNT(*) FROM notification WHERE is_read = 0"
    ).fetchone()[0]


def mark_read(notification_id: int) -> None:
    c = _conn()
    c.execute("UPDATE notification SET is_read = 1 WHERE id = ?", (notification_id,))
    c.commit()


def mark_all_read() -> None:
    c = _conn()
    c.execute("UPDATE notification SET is_read = 1")
    c.commit()
