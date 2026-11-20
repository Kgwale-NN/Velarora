"""Group updates operations."""
from __future__ import annotations
from backend.db._core import _conn, _now


def get_or_create_group(name: str, description: str = "") -> int:
    """Return the id of an existing group with this name, or create one."""
    c = _conn()
    row = c.execute("SELECT id FROM computer_group WHERE name = ?", (name,)).fetchone()
    if row:
        return row["id"]
    return create_group(name, description)


def create_group(name: str, description: str = "") -> int:
    c = _conn()
    with c:
        cur = c.execute(
            "INSERT INTO computer_group (name, description, created_at) VALUES (?, ?, ?)",
            (name, description or None, _now()),
        )
    return cur.lastrowid


def update_group(group_id: int, name: str, description: str = "") -> None:
    c = _conn()
    with c:
        cur = c.execute(
            "UPDATE computer_group SET name = ?, description = ? WHERE id = ?",
            (name, description or None, group_id),
        )
        if cur.rowcount == 0:
            raise ValueError('This group no longer exists. Refresh the page and try again.')


def delete_group(group_id: int) -> None:
    """Delete a group; membership rows cascade-delete via computer_group_member."""
    c = _conn()
    if c.execute("SELECT 1 FROM monitoring_run WHERE classroom_id=? AND status='running' LIMIT 1",(group_id,)).fetchone():
        raise ValueError("End the classroom’s running exam before deleting it.")
    c.execute("DELETE FROM computer_group WHERE id = ?", (group_id,))
    c.commit()


def add_computer_to_group(computer_id: int, group_id: int) -> None:
    """Add a computer to a group (idempotent — safe to call multiple times)."""
    c = _conn()
    c.execute(
        "INSERT OR IGNORE INTO computer_group_member (computer_id, group_id) VALUES (?, ?)",
        (computer_id, group_id),
    )
    c.commit()


def remove_computer_from_group(computer_id: int, group_id: int) -> None:
    """Remove a computer from a specific group (does not affect other groups)."""
    c = _conn()
    c.execute(
        "DELETE FROM computer_group_member WHERE computer_id = ? AND group_id = ?",
        (computer_id, group_id),
    )
    c.commit()
