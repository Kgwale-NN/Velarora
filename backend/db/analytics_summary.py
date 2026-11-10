"""Analytics summary operations."""
from __future__ import annotations
from typing import Optional
from backend.db._core import _conn
from backend.db.analytics_filters import _analytics_where


def get_summary_stats(
    computer_id: Optional[int] = None,
    user_id:     Optional[int] = None,
    from_date:   str           = "",
    to_date:     str           = "",
) -> dict:
    w, p = _analytics_where(computer_id, user_id, from_date, to_date)
    c = _conn()
    base   = f"FROM detection_event e LEFT JOIN user u ON u.id=e.user_id {w}"
    total  = c.execute(f"SELECT COUNT(*) {base}", p).fetchone()[0]
    and_or = "AND" if w else "WHERE"
    hits   = c.execute(
        f"SELECT COUNT(*) {base} {and_or} e.had_detection=1", p
    ).fetchone()[0]
    students = c.execute(
        f"SELECT COUNT(DISTINCT COALESCE(e.user_id, e.os_username)) {base}", p
    ).fetchone()[0]
    row = c.execute(f"""
        SELECT dc.name, COUNT(*) AS cnt
        FROM detection d
        JOIN detection_event e  ON e.id  = d.event_id
        JOIN detection_class dc ON dc.id = d.class_id
        LEFT JOIN user u        ON u.id  = e.user_id
        {w}
        GROUP BY dc.name ORDER BY cnt DESC LIMIT 1
    """, p).fetchone()
    top_class = row[0] if row else "—"
    return {
        "total_events":     total,
        "detection_events": hits,
        "active_students":  students,
        "top_class":        top_class,
    }


def get_class_distribution(
    computer_id: Optional[int] = None,
    user_id:     Optional[int] = None,
    from_date:   str           = "",
    to_date:     str           = "",
) -> list[dict]:
    w, p = _analytics_where(computer_id, user_id, from_date, to_date)
    c = _conn()
    rows = c.execute(f"""
        SELECT dc.name, dc.color_hex, COUNT(*) AS cnt
        FROM detection d
        JOIN detection_event e  ON e.id  = d.event_id
        JOIN detection_class dc ON dc.id = d.class_id
        LEFT JOIN user u        ON u.id  = e.user_id
        {w}
        GROUP BY dc.name, dc.color_hex
        ORDER BY cnt DESC
    """, p).fetchall()
    return [{"name": r[0], "color": r[1], "count": r[2]} for r in rows]
