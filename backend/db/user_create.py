"""User create operations."""
from __future__ import annotations
from typing import Optional
from backend.db._core import _conn, _now
from backend.db.user_passwords import _hash_pw
from backend.db.user_queries import get_role_id
from backend.db.user_passwords import validate_password


def create_user(
    username:      str,
    password:      str,
    role:          str,
    created_by_id: Optional[int] = None,
    is_active:     bool          = True,
    email: Optional[str] = None,
) -> int:
    """
    Insert the user row and audit entry in a single transaction.
    Returns the new user id.

    Historical event assignment is intentionally NOT done here — call
    auto_assign_user_events(username, new_id) separately (ideally in a
    background task) so this function stays fast.
    """
    from backend.db.audit import _insert_audit
    role_id = get_role_id(role)
    if role_id is None:
        raise ValueError(f"Unknown role: {role!r}")
    from backend.db.staff_email import normalize_email
    email = normalize_email(email) if email is not None else None
    validate_password(password)
    c = _conn()
    cur = c.execute(
        "INSERT INTO user (username, hashed_password, role_id, is_active, created_by, created_at, email) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (username, _hash_pw(password), role_id, 1 if is_active else 0,
         created_by_id, _now(), email),
    )
    new_id = cur.lastrowid
    _insert_audit(c, "user.create", entity="user", entity_id=new_id,
                  detail=f"role={role}, active={is_active}, created_by={created_by_id}")
    c.commit()
    return new_id


def auto_create_student(username: str) -> int:
    """
    Create an inactive student account for a detected OS username.
    Uses INSERT OR IGNORE so concurrent calls are safe.
    Historical event assignment is intentionally NOT done here — it is
    deferred to activate_user() so the IO worker thread never holds a
    long write lock while other threads also need to write.

    Returns the user id (new or pre-existing). Raises RuntimeError on the
    truly unexpected "row vanished between INSERT and SELECT" case rather
    than silently returning -1 — historically callers used the result as
    a foreign key and `-1` slipped into detection_event.user_id.
    """
    import secrets
    from backend.db.audit import _insert_audit
    role_id = get_role_id("student")
    if role_id is None:
        raise ValueError("Role 'student' not found")
    # Random password — cannot be used to log in (is_active=0 blocks login)
    random_pw = secrets.token_hex(32)
    c = _conn()
    cur = c.execute(
        "INSERT OR IGNORE INTO user "
        "(username, hashed_password, role_id, is_active, created_at) "
        "VALUES (?, ?, ?, 0, ?)",
        (username, _hash_pw(random_pw), role_id, _now()),
    )
    if cur.rowcount > 0:
        new_id = cur.lastrowid
        _insert_audit(c, "user.auto_create", entity="user", entity_id=new_id,
                      detail="auto-created inactive student from OS login")
    c.commit()
    row = c.execute("SELECT id FROM user WHERE username = ?", (username,)).fetchone()
    if row is None:
        raise RuntimeError(
            f"auto_create_student: user {username!r} not found after "
            "INSERT OR IGNORE — DB inconsistent"
        )
    return int(row["id"])
