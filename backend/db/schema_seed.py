"""Initial detection classes and administrator account."""
from backend.db._core import _conn, _now

DEFAULT_CLASSES: list[dict] = [
    {"name": "DI",                "color": "#00ff00"},
    {"name": "Ekrano nuotraukos", "color": "#ff8000"},
    {"name": "Narsykle",          "color": "#0080ff"},
    {"name": "Notepad",           "color": "#8000ff"},
    {"name": "Paint",             "color": "#00ffff"},
    {"name": "PowerPoint",        "color": "#ff0080"},
    {"name": "Word",              "color": "#40c840"},
]


def seed_classes() -> None:
    """Seed default detection classes only if the table is completely empty."""
    c = _conn()
    if c.execute("SELECT COUNT(*) FROM detection_class").fetchone()[0] == 0:
        now = _now()
        c.executemany(
            "INSERT OR IGNORE INTO detection_class (name, color_hex, created_at) "
            "VALUES (:name, :color, :now)",
            [{**cls, "now": now} for cls in DEFAULT_CLASSES],
        )
        c.commit()


def ensure_default_admin(username: str, password: str, email: str | None = None) -> None:
    """
    Create the initial admin account when no users exist yet. Both arguments
    are required — there is no fallback to a hard-coded credential. The
    bootstrap layer (`backend/main.py:_bootstrap_admin`) is responsible for
    sourcing them from the environment.
    """
    from backend.db.users import _hash_pw
    if not username or not password:
        raise ValueError("ensure_default_admin requires both username and password")
    c = _conn()
    if c.execute("SELECT COUNT(*) FROM user").fetchone()[0] == 0:
        role_row = c.execute("SELECT id FROM role WHERE name='admin'").fetchone()
        if role_row:
            from backend.db.user_passwords import validate_password
            validate_password(password)
            c.execute(
                "INSERT INTO user (username, hashed_password, role_id, created_at, email) "
                "VALUES (?, ?, ?, ?, ?)",
                (username, _hash_pw(password), role_row["id"], _now(), email),
            )
            c.commit()

ensure_default_teacher = ensure_default_admin
