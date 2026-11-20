"""Analytics filters operations."""
from __future__ import annotations
from typing import Optional
from backend.db.teacher_scope import event_scope


def _analytics_where(
    computer_id: Optional[int],
    user_id:     Optional[int],
    from_date:   str,
    to_date:     str,
) -> tuple[str, list]:
    clauses: list[str] = []
    params:  list      = []
    scope, scope_params = event_scope('e')
    clauses.append(scope)
    params.extend(scope_params)
    if computer_id:
        clauses.append("e.computer_id = ?"); params.append(computer_id)
    if user_id:
        clauses.append("e.user_id = ?");     params.append(user_id)
    if from_date:
        clauses.append("e.detected_at >= ?"); params.append(from_date + " 00:00:00")
    if to_date:
        clauses.append("e.detected_at <= ?"); params.append(to_date + " 23:59:59")
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


def _event_joins_where(
    computer_id: Optional[int],
    user_id:     Optional[int],
    class_name:  str,
    only_hits:   bool,
) -> tuple[list[str], list[str], list]:
    """Shared JOIN/WHERE logic for query_events and count_query_events."""
    joins:   list[str] = ["detection_event e"]
    clauses: list[str] = []
    params:  list      = []

    joins.append("JOIN computer c ON c.id = e.computer_id")
    joins.append("LEFT JOIN user u ON u.id = e.user_id")
    joins.append("LEFT JOIN ml_model mm ON mm.id = e.model_id")

    if class_name:
        joins.append(
            "JOIN detection d ON d.event_id = e.id "
            "JOIN detection_class dc ON dc.id = d.class_id"
        )
        clauses.append("dc.name = ?"); params.append(class_name)
    else:
        joins.append("LEFT JOIN detection d ON d.event_id = e.id")
        joins.append("LEFT JOIN detection_class dc ON dc.id = d.class_id")

    if computer_id:
        clauses.append("e.computer_id = ?"); params.append(computer_id)
    if user_id:
        clauses.append("e.user_id = ?");     params.append(user_id)
    if only_hits:
        clauses.append("e.had_detection = 1")

    return joins, clauses, params
