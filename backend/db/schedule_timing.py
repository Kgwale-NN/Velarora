"""Schedule timing operations."""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from backend.db._core import _conn
from backend.db.schedule_queries import list_schedules


def find_overlapping_schedules(
    days:       str,
    start_time: str,
    end_time:   str,
    exclude_id: Optional[int] = None,
) -> list[dict]:
    """
    Return ALL schedules (any group) that overlap with the given window.
    Two windows overlap when they share ≥1 day AND new_start < existing_end AND
    existing_start < new_end  (standard interval-overlap test).
    The check is global because the monitor is a single shared process — overlapping
    schedules across different groups are just as ambiguous as within one group.
    Pass exclude_id=<id> when editing to skip the schedule being modified.
    """
    existing = list_schedules()
    new_days = {d for d in days.split(",") if d}
    result = []
    for s in existing:
        if exclude_id is not None and s["id"] == exclude_id:
            continue
        existing_days = {d for d in s["days_of_week"].split(",") if d}
        if not new_days & existing_days:
            continue
        if start_time < s["end_time"] and s["start_time"] < end_time:
            result.append(s)
    return result


def get_active_schedules_now() -> list[dict]:
    """
    Return all is_active schedules whose day-of-week and time window
    match the current local time.  Used by a background ticker to decide
    whether to auto-start monitoring.
    """
    now   = datetime.now()
    today = str(now.weekday())          # 0=Mon … 6=Sun
    hhmm  = now.strftime("%H:%M")

    c = _conn()
    rows = c.execute("""
        SELECT s.*, g.name AS group_name
        FROM   schedule s
        LEFT JOIN computer_group g ON g.id = s.group_id
        WHERE  s.is_active = 1
          AND  s.start_time <= ? AND ? < s.end_time
    """, (hhmm, hhmm)).fetchall()

    return [
        dict(r) for r in rows
        if today in r["days_of_week"].split(",")
    ]
