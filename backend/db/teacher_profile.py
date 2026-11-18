"""Allow an active teacher to rename their own display identity without changing sign-in data."""
import sqlite3
from backend.db._core import _conn
from backend.db.audit import _insert_audit


def update_teacher_name(user_id: int, username: str) -> str:
    name = (username or '').strip()
    if not name or len(name) > 100:
        raise ValueError('Enter a name between 1 and 100 characters.')
    c = _conn()
    try:
        with c:
            changed = c.execute(
                "UPDATE user SET username=? WHERE id=? AND is_active=1 "
                "AND role_id=(SELECT id FROM role WHERE name='teacher')", (name,user_id))
            if changed.rowcount != 1:
                raise ValueError('An active teacher account is required.')
            _insert_audit(c,'user.profile_update',user_id=user_id,entity='user',entity_id=user_id)
    except sqlite3.IntegrityError as exc:
        raise ValueError('This name is already in use. Choose another name.') from exc
    return name
