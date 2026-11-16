"""Match Google's verified identity to an existing active Velarora account."""
import sqlite3

from backend.db._core import _conn


def google_account(claims):
    email = claims.get("email", "")
    subject = claims.get("sub")
    if not subject or claims.get("email_verified") is not True or not isinstance(email, str):
        return None
    # Google controls Gmail and confirms the domain for Workspace accounts.
    if not (email.lower().endswith("@gmail.com") or claims.get("hd")):
        return None
    conn = _conn()
    try:
        with conn:
            changed = conn.execute(
                "UPDATE user SET google_subject=? WHERE email=? COLLATE NOCASE "
                "AND is_active=1 AND (google_subject IS NULL OR google_subject=?)",
                (subject, email, subject),
            )
            if changed.rowcount != 1:
                return None
            row = conn.execute(
                "SELECT u.id, u.username, r.name AS role FROM user u JOIN role r ON r.id=u.role_id "
                "WHERE u.google_subject=?", (subject,),
            ).fetchone()
            return dict(row)
    except sqlite3.IntegrityError:
        return None
