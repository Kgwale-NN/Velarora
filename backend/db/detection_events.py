"""Detection events operations."""
from __future__ import annotations
from typing import Optional
from backend.db._core import _conn, _now


def list_classes() -> list[dict]:
    c = _conn()
    return [dict(r) for r in c.execute(
        "SELECT * FROM detection_class ORDER BY name"
    ).fetchall()]


def get_class_by_model_index(model_id: int, class_index: int) -> Optional[dict]:
    c = _conn()
    row = c.execute("""
        SELECT dc.*
        FROM   model_class mc
        JOIN   detection_class dc ON dc.id = mc.class_id
        WHERE  mc.model_id = ? AND mc.class_index = ?
    """, (model_id, class_index)).fetchone()
    return dict(row) if row else None


def insert_event(
    computer_id:      int,
    dets:             list[dict],
    user_id:          Optional[int]   = None,
    os_username: Optional[str]   = None,
    frame_bytes:      Optional[bytes] = None,
    model_id:         Optional[int]   = None,
    run_id:           Optional[int]   = None,
    _commit:          bool            = True,
    foreground_app: Optional[str] = None,
) -> int:
    """
    Write one detection_event row + one detection row per bounding box.
    Always called — even when dets is empty (had_detection = 0).

    Pass _commit=False from a batching caller to coalesce many events into a
    single transaction (one fsync). The caller must call conn.commit()
    afterwards — all inserts up to that point share one WAL transaction.
    """
    c = _conn()
    cur = c.execute(
        "INSERT INTO detection_event "
        "(computer_id, user_id, model_id, run_id, os_username, detected_at, frame_blob, had_detection, foreground_app) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (computer_id, user_id, model_id, run_id, os_username, _now(),
         frame_bytes, 1 if dets else 0, foreground_app),
    )
    event_id = cur.lastrowid
    for d in dets:
        if model_id is None:
            continue
        cls_row = c.execute(
            "SELECT mc.class_id FROM model_class mc "
            "WHERE mc.model_id = ? AND mc.class_index = ?",
            (model_id, d["class_id"]),
        ).fetchone()
        if cls_row is None:
            continue
        c.execute(
            "INSERT INTO detection "
            "(event_id, class_id, confidence, box_x1, box_y1, box_x2, box_y2) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (event_id, cls_row[0], d["conf"], *d["box"]),
        )
    if _commit:
        c.commit()
    return event_id
