"""Analytics activity operations."""
from __future__ import annotations
from typing import Optional
from backend.db._core import _conn
from backend.db.analytics_filters import _analytics_where


def get_daily_detections(
    computer_id: Optional[int] = None,
    user_id:     Optional[int] = None,
    from_date:   str           = "",
    to_date:     str           = "",
) -> list[dict]:
    w, p = _analytics_where(computer_id, user_id, from_date, to_date)
    c = _conn()
    rows = c.execute(f"""
        SELECT
            SUBSTR(e.detected_at, 1, 10) AS day,
            COUNT(*)                     AS total,
            SUM(e.had_detection)         AS hits
        FROM detection_event e
        LEFT JOIN user u ON u.id = e.user_id
        {w}
        GROUP BY day
        ORDER BY day
    """, p).fetchall()
    return [{"day": r[0], "total": r[1], "hits": r[2]} for r in rows]


def get_student_activity(
    computer_id: Optional[int] = None,
    from_date:   str           = "",
    to_date:     str           = "",
) -> list[dict]:
    w, p = _analytics_where(computer_id, None, from_date, to_date)
    and_or = "AND" if w else "WHERE"
    c = _conn()
    rows = c.execute(f"""
        SELECT
            COALESCE(u.username, e.os_username, '(unknown)') AS student,
            COUNT(*) AS hits
        FROM detection_event e
        LEFT JOIN user u ON u.id = e.user_id
        {w} {and_or} e.had_detection = 1
        GROUP BY student
        ORDER BY hits DESC
        LIMIT 20
    """, p).fetchall()
    return [{"student": r[0], "hits": r[1]} for r in rows]


def count_events_for_user(user_id: int) -> int:
    """Fast O(index) count of detection_event rows assigned to a user."""
    c = _conn()
    return c.execute(
        "SELECT COUNT(*) FROM detection_event WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
