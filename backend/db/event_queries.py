"""Event queries operations."""
from __future__ import annotations
from typing import Optional
from backend.db._core import _conn


def query_events(
    computer_id: Optional[int] = None,
    user_id:     Optional[int] = None,
    class_name:  str           = "",
    only_hits:   bool          = False,
    limit:       int           = 200,
    offset:      int           = 0,
) -> list[dict]:
    """
    Two-step query so SQLite never reads frame_blob during the ID scan:

    Step 1 — fetch matching event IDs using covering indexes on detection_event.
             Filters on simple columns (user_id, computer_id, had_detection) map
             directly to existing composite indexes; class-name filtering uses a
             subquery. The blob column is never touched in this step.

    Step 2 — fetch full details (including has_frame) for exactly those N rows.
    """
    c = _conn()

    # ── Step 1: get IDs via indexes ───────────────────────────────────────────
    id_clauses: list[str] = []
    id_params:  list      = []

    if computer_id:
        id_clauses.append("computer_id = ?");   id_params.append(computer_id)
    if user_id:
        id_clauses.append("user_id = ?");        id_params.append(user_id)
    if only_hits:
        id_clauses.append("had_detection = 1")
    if class_name:
        id_clauses.append(
            "id IN (SELECT d.event_id FROM detection d "
            "JOIN detection_class dc ON dc.id = d.class_id WHERE dc.name = ?)"
        )
        id_params.append(class_name)

    id_where = ("WHERE " + " AND ".join(id_clauses)) if id_clauses else ""
    id_params.extend([limit, offset])

    ids = [r[0] for r in c.execute(f"""
        SELECT id FROM detection_event
        {id_where}
        ORDER BY detected_at DESC
        LIMIT ? OFFSET ?
    """, id_params).fetchall()]

    if not ids:
        return []

    # ── Step 2: full detail fetch for only those N rows ───────────────────────
    ph = ",".join("?" * len(ids))
    rows = c.execute(f"""
        SELECT
            e.id                AS event_id,
            e.detected_at,
            c.name              AS computer,
            COALESCE(u.username, e.os_username, '—') AS student,
            e.had_detection,
            COALESCE(e.foreground_app, '—') AS foreground_app,
            CASE WHEN e.frame_blob IS NOT NULL THEN 1 ELSE 0 END AS has_frame,
            GROUP_CONCAT(dc.name || ' (' || ROUND(d.confidence*100) || '%)', ', ')
                                AS detections,
            mm.name             AS model_name
        FROM detection_event e
        JOIN computer c ON c.id = e.computer_id
        LEFT JOIN user u ON u.id = e.user_id
        LEFT JOIN ml_model mm ON mm.id = e.model_id
        LEFT JOIN detection d ON d.event_id = e.id
        LEFT JOIN detection_class dc ON dc.id = d.class_id
        WHERE e.id IN ({ph})
        GROUP BY e.id
        ORDER BY e.detected_at DESC
    """, ids).fetchall()

    return [dict(r) for r in rows]
