"""Update the administrator's display name without changing email or history."""
import sqlite3
from backend.db._core import _conn
from backend.db.audit import _insert_audit


def update_admin_name(user_id: int, username: str) -> str:
    name = username.strip()
    if not name or len(name) > 100:
        raise ValueError("Enter a name between 1 and 100 characters.")
    conn = _conn()
    try:
        with conn:
            changed = conn.execute(
                "UPDATE user SET username=? WHERE id=? AND is_active=1 "
                "AND role_id=(SELECT id FROM role WHERE name='admin')",
                (name, user_id),
            )
            if changed.rowcount != 1:
                raise ValueError("Select an active administrator account.")
            _insert_audit(conn, "user.profile_update", user_id=user_id, entity="user", entity_id=user_id)
    except sqlite3.IntegrityError as exc:
        raise ValueError("This username is already in use.") from exc
    return name
