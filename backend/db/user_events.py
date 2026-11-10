"""User events operations."""
from __future__ import annotations
from backend.db._core import _conn


def _batched_update(sql: str, params: tuple, batch_size: int) -> int:
    """
    Execute `sql` in a loop, committing after each pass, until a pass updates
    fewer than `batch_size` rows. Keeps the SQLite write lock held for only a
    few milliseconds at a time so concurrent IO-worker writes aren't blocked.

    `sql` must end with `LIMIT ?` and the final element of `params` must be
    `batch_size`. Returns the total number of rows updated across all passes.
    """
    c = _conn()
    total = 0
    while True:
        cur = c.execute(sql, params)
        c.commit()
        n = cur.rowcount
        total += n
        if n < batch_size:
            return total


def auto_assign_user_events(username: str, user_id: int, batch_size: int = 500) -> int:
    """
    Assign all anonymous detection_event rows whose os_username matches
    *username* (case-insensitive) to *user_id*. Returns the total updated.
    """
    return _batched_update(
        """
        UPDATE detection_event SET user_id = ?
        WHERE id IN (
            SELECT id FROM detection_event
            WHERE LOWER(os_username) = LOWER(?) AND user_id IS NULL
            LIMIT ?
        )
        """,
        (user_id, username, batch_size),
        batch_size,
    )


def nullify_user_events(user_id: int, batch_size: int = 500) -> int:
    """
    Set user_id = NULL on all detection_event rows for *user_id* before the
    user row is deleted, so the subsequent DELETE has no ON DELETE SET NULL
    cascade work to do. Returns the total cleared.
    """
    return _batched_update(
        """
        UPDATE detection_event SET user_id = NULL
        WHERE id IN (
            SELECT id FROM detection_event WHERE user_id = ? LIMIT ?
        )
        """,
        (user_id, batch_size),
        batch_size,
    )
