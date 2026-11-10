"""Alert rules operations."""
from __future__ import annotations
from backend.db._core import _conn


def list_alert_rules() -> list[dict]:
    """All detection classes with their notification_enabled flag."""
    c = _conn()
    rows = c.execute("""
        SELECT
            dc.id  AS class_id,
            dc.name,
            dc.color_hex,
            dc.notification_enabled AS enabled
        FROM detection_class dc
        ORDER BY dc.name
    """).fetchall()
    return [dict(r) for r in rows]


def set_alert_rule(class_id: int, enabled: bool) -> None:
    """Toggle the notification_enabled flag for a single detection class.

    Raises ValueError if `class_id` does not correspond to an existing row —
    silently no-op'ing was hiding bad UI state (stale dropdown values after a
    class was deleted, etc.).
    """
    from backend.db.audit import _insert_audit
    c = _conn()
    cur = c.execute(
        "UPDATE detection_class SET notification_enabled = ? WHERE id = ?",
        (1 if enabled else 0, class_id),
    )
    if cur.rowcount == 0:
        raise ValueError(f"detection_class id={class_id!r} does not exist")
    _insert_audit(c, "alert.rule", entity="detection_class", entity_id=class_id,
                  detail="enabled" if enabled else "disabled")
    c.commit()
    # Drop the in-process alert-rule cache so detect worker picks up the change
    # on the very next frame instead of waiting for the TTL to expire.
    try:
        from backend.services.alert_service import invalidate_prohibited_cache
        invalidate_prohibited_cache()
    except Exception:
        pass
