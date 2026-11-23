"""Run lifecycle operations."""
from __future__ import annotations
from typing import Optional
from backend.db._core import _conn, _now


def create_run(
    trigger_type: str            = "manual",
    schedule_id:  Optional[int]  = None,
    group_name:   Optional[str]  = None,
    model_id:     Optional[int]  = None,
    started_by:   Optional[int]  = None,
) -> int:
    c = _conn()
    with c:
        cur = c.execute(
            "INSERT INTO monitoring_run "
            "(trigger_type, schedule_id, group_name, model_id, started_by, "
            " status, started_at) "
            "VALUES (?, ?, ?, ?, ?, 'running', ?)",
            (trigger_type, schedule_id, group_name, model_id, started_by, _now()),
        )
    return cur.lastrowid


def set_run_model(run_id: int, model_id: Optional[int]) -> None:
    """
    Record which model the session actually runs with. Called from the detect
    worker after it resolves schedule-pinned vs. currently-active model —
    the run row is created before that resolution happens.
    """
    c = _conn()
    with c:
        c.execute(
            "UPDATE monitoring_run SET model_id = ? WHERE id = ?",
            (model_id, run_id),
        )


def finish_run(run_id: int, status: str = "finished") -> None:
    """Mark the run ended now. No-op if the run is already finished."""
    c = _conn()
    with c:
        c.execute(
            "UPDATE monitoring_run SET status = ?, ended_at = ? "
            "WHERE id = ? AND status = 'running'",
            (status, _now(), run_id),
        )


def finish_stale_runs() -> int:
    """
    Repair runs left in 'running' state by a process crash or hard kill.
    Called once at startup, before the scheduler can start a new session.
    ended_at falls back to the run's last event time (or started_at when the
    run never produced events) — closest available approximation of when
    monitoring actually died.
    """
    c = _conn()
    cur = c.execute("""
        UPDATE monitoring_run
        SET status   = 'interrupted',
            ended_at = COALESCE(
                (SELECT MAX(e.detected_at) FROM detection_event e
                 WHERE e.run_id = monitoring_run.id),
                started_at
            )
        WHERE status = 'running'
    """)
    c.commit()
    return cur.rowcount
