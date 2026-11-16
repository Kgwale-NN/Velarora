"""User updates operations."""
from __future__ import annotations
from backend.db._core import _conn
from backend.db.user_passwords import _hash_pw
from backend.db.user_events import auto_assign_user_events
from backend.db.user_passwords import validate_password


def activate_user(user_id: int, new_password: str, email: str | None = None) -> None:
    """
    Set a real password and mark the user active so they can log in.
    Also assigns any historical anonymous events that match this user's
    username (safe here because this runs in a UI executor thread, not
    a hot-path IO worker).
    """
    from backend.db.audit import _insert_audit
    from backend.db.staff_email import normalize_email
    email = normalize_email(email) if email is not None else None
    validate_password(new_password)
    c = _conn()
    row = c.execute("SELECT username FROM user WHERE id = ?", (user_id,)).fetchone()
    with c:
        changed = c.execute(
            "UPDATE user SET hashed_password = ?, is_active = 1, email = COALESCE(?, email) "
            "WHERE id = ? AND role_id=(SELECT id FROM role WHERE name='student') AND is_active=0",
            (_hash_pw(new_password), email, user_id),
        )
        if changed.rowcount != 1:
            raise ValueError("Select an inactive student account.")
        _insert_audit(c, "user.activate", entity="user", entity_id=user_id)
    if row:
        auto_assign_user_events(row["username"], user_id)


def update_password(user_id: int, new_password: str) -> None:
    from backend.db.audit import _insert_audit
    validate_password(new_password)
    c = _conn()
    c.execute(
        "UPDATE user SET hashed_password = ? WHERE id = ?",
        (_hash_pw(new_password), user_id),
    )
    _insert_audit(c, "user.password_change", entity="user", entity_id=user_id)
    c.commit()


def delete_user(user_id: int) -> None:
    from backend.db.audit import _insert_audit
    c = _conn()
    c.execute("DELETE FROM user WHERE id = ?", (user_id,))
    _insert_audit(c, "user.delete", entity="user", entity_id=user_id)
    c.commit()
