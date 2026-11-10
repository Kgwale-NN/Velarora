"""Detection assignment operations."""
from __future__ import annotations
from backend.db._core import _conn


def count_anonymous_events(computer_id: int) -> int:
    c = _conn()
    return c.execute(
        "SELECT COUNT(*) FROM detection_event "
        "WHERE computer_id = ? AND user_id IS NULL",
        (computer_id,),
    ).fetchone()[0]


def assign_anonymous_events(user_id: int, computer_id: int) -> int:
    """Manually assign anonymous events on a specific computer to a user."""
    c = _conn()
    cur = c.execute(
        "UPDATE detection_event SET user_id = ? "
        "WHERE computer_id = ? AND user_id IS NULL",
        (user_id, computer_id),
    )
    c.commit()
    return cur.rowcount
