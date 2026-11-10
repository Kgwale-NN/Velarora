"""Group queries operations."""
from __future__ import annotations
from typing import Optional
from backend.db._core import _conn


def list_groups() -> list[dict]:
    c = _conn()
    rows = c.execute("""
        SELECT g.*,
               COUNT(cgm.computer_id) AS computer_count
        FROM   computer_group g
        LEFT JOIN computer_group_member cgm ON cgm.group_id = g.id
        GROUP BY g.id
        ORDER BY g.name
    """).fetchall()
    return [dict(r) for r in rows]


def get_group(group_id: int) -> Optional[dict]:
    c = _conn()
    row = c.execute(
        "SELECT * FROM computer_group WHERE id = ?", (group_id,)
    ).fetchone()
    return dict(row) if row else None


def list_computers_in_group(group_id: int) -> list[dict]:
    c = _conn()
    rows = c.execute("""
        SELECT comp.*
        FROM   computer comp
        JOIN   computer_group_member cgm ON cgm.computer_id = comp.id
        WHERE  cgm.group_id = ?
        ORDER  BY comp.name
    """, (group_id,)).fetchall()
    return [dict(r) for r in rows]
