"""Run queries operations."""
from __future__ import annotations
from typing import Optional
from backend.db._core import _conn
from backend.db.teacher_scope import owner_id, require_run


_RUN_SELECT = """
    SELECT r.id, r.trigger_type, r.schedule_id, r.group_name, r.model_id,
           r.started_by, r.status, r.started_at, r.ended_at,
           s.name  AS schedule_name,
           m.name  AS model_name,
           u.username AS started_by_name,
           (SELECT COUNT(*) FROM detection_event e
            WHERE e.run_id = r.id)                          AS total_events,
           (SELECT COUNT(*) FROM detection_event e
            WHERE e.run_id = r.id AND e.had_detection = 1)  AS detection_events,
           (SELECT COUNT(*) FROM notification n
            JOIN detection_event e2 ON e2.id = n.event_id
            WHERE e2.run_id = r.id)                         AS alert_count,
           (SELECT COUNT(DISTINCT e.computer_id) FROM detection_event e
            WHERE e.run_id = r.id)                          AS computer_count,
           (SELECT COUNT(DISTINCT COALESCE(e.user_id, e.os_username))
            FROM detection_event e
            WHERE e.run_id = r.id
              AND (e.user_id IS NOT NULL OR e.os_username IS NOT NULL))
                                                            AS student_count
    FROM monitoring_run r
    LEFT JOIN schedule s ON s.id = r.schedule_id
    LEFT JOIN ml_model m ON m.id = r.model_id
    LEFT JOIN user     u ON u.id = r.started_by
"""


def list_runs(limit: int = 100) -> list[dict]:
    c = _conn()
    uid = owner_id()
    where, params = ("WHERE r.started_by=? ",[uid]) if uid is not None else ("",[])
    rows = c.execute(
        _RUN_SELECT + where + "ORDER BY r.id DESC LIMIT ?", params+[limit]
    ).fetchall()
    return [dict(r) for r in rows]


def get_run(run_id: int) -> Optional[dict]:
    c = _conn()
    require_run(run_id)
    row = c.execute(_RUN_SELECT + "WHERE r.id = ?", (run_id,)).fetchone()
    return dict(row) if row else None


def run_short_label(run: dict, manual_label: str) -> str:
    """
    Short identifier for a run, used in report titles. Combines a name with the
    run's date and time window (more meaningful than a bare sequence number):
      • scheduler-triggered runs → "{schedule name} {date} {start}–{end}"
        (falls back to the manual name if the schedule was deleted),
      • manual runs              → "{manual_label} {date} {start}–{end}".

    A still-running session shows "…" as the end time. `manual_label` is passed
    in (already translated) so this stays UI-agnostic. Falls back to the bare
    name (no window) if the timestamps are missing/malformed.
    """
    if run.get("trigger_type") == "schedule" and run.get("schedule_name"):
        name = run["schedule_name"]
    else:
        name = manual_label

    started = run.get("started_at") or ""
    ended   = run.get("ended_at")
    # Stored format is "YYYY-MM-DD HH:MM:SS"; slice defensively.
    date     = started[:10]
    start_hm = started[11:16]
    end_hm   = ended[11:16] if ended else "…"
    if not date or not start_hm:
        return name
    return f"{name} | {date} {start_hm}–{end_hm}"
