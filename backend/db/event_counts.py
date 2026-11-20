"""Event counts operations."""
from __future__ import annotations
from typing import Optional
from backend.db.teacher_scope import event_scope
from backend.db._core import _conn


def count_query_events(
    computer_id: Optional[int] = None,
    user_id:     Optional[int] = None,
    class_name:  str           = "",
    only_hits:   bool          = False,
) -> int:
    """
    Fast count using the same index-only approach as query_events step 1.
    No blob reads, no GROUP BY, no heavy JOINs unless class_name is given.
    """
    clauses: list[str] = []
    params:  list      = []
    scope, scope_params = event_scope('')
    clauses.append(scope)
    params.extend(scope_params)

    if computer_id:
        clauses.append("computer_id = ?"); params.append(computer_id)
    if user_id:
        clauses.append("user_id = ?");     params.append(user_id)
    if only_hits:
        clauses.append("had_detection = 1")
    if class_name:
        clauses.append(
            "(id IN (SELECT d.event_id FROM detection d "
            "JOIN detection_class dc ON dc.id = d.class_id WHERE dc.name = ?) OR "
            "id IN (SELECT n.event_id FROM notification n JOIN detection_class dc ON dc.id=n.class_id WHERE dc.name=?))"
        )
        params.extend([class_name,class_name])

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    c = _conn()
    return c.execute(
        f"SELECT COUNT(*) FROM detection_event {where}", params
    ).fetchone()[0]
