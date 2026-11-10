"""User updates operations."""
from __future__ import annotations
from backend.db._core import _conn
from backend.db.user_passwords import _hash_pw
from backend.db.user_events import auto_assign_user_events
from backend.db.user_passwords import validate_password


def activate_user(user_id: int, new_password: str) -> None:
    """
    Set a real password and mark the user active so they can log in.
    Also assigns any historical anonymous events that match this user's
    username (safe here because this runs in a UI executor thread, not
    a hot-path IO worker).
    """
    from backend.db.audit import _insert_audit
    validate_password(new_password)
    c = _conn()
    row = c.execute("SELECT username FROM user WHERE id = ?", (user_id,)).fetchone()
    c.execute(
        "UPDATE user SET hashed_password = ?, is_active = 1 WHERE id = ?",
        (_hash_pw(new_password), user_id),
    )
    _insert_audit(c, "user.activate", entity="user", entity_id=user_id)
    c.commit()
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
