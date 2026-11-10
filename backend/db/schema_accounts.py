"""SQL table definitions; loaded by schema.init_db."""
SQL = """
        -- roles ──────────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS role (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT    NOT NULL UNIQUE
        );

        -- users ──────────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS user (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            username        TEXT    NOT NULL UNIQUE,
            hashed_password TEXT    NOT NULL,
            role_id         INTEGER NOT NULL REFERENCES role(id),
            is_active       INTEGER NOT NULL DEFAULT 1,
            created_by      INTEGER REFERENCES user(id) ON DELETE SET NULL,
            created_at      TEXT    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_user_role ON user(role_id);

        -- computer groups ─────────────────────────────────────────────────────
        -- Logical groupings: Lab 1, Exam Room, etc.
        CREATE TABLE IF NOT EXISTS computer_group (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL UNIQUE,
            description TEXT,
            created_at  TEXT    NOT NULL
        );

        -- computers ───────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS computer (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT    NOT NULL UNIQUE,
            host_address TEXT    NOT NULL,
            created_at   TEXT    NOT NULL
        );

        -- computer ↔ group membership (many-to-many) ──────────────────────────
        CREATE TABLE IF NOT EXISTS computer_group_member (
            computer_id INTEGER NOT NULL REFERENCES computer(id) ON DELETE CASCADE,
            group_id    INTEGER NOT NULL REFERENCES computer_group(id) ON DELETE CASCADE,
            PRIMARY KEY (computer_id, group_id)
        );
        CREATE INDEX IF NOT EXISTS idx_cgm_computer ON computer_group_member(computer_id);
        CREATE INDEX IF NOT EXISTS idx_cgm_group    ON computer_group_member(group_id);
"""
