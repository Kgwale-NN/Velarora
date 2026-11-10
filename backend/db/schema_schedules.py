"""SQL table definitions; loaded by schema.init_db."""
SQL = """

        -- monitoring schedules ────────────────────────────────────────────────
        -- When to automatically start/stop monitoring a group.
        -- days_of_week: comma-separated 0-6 (0=Mon … 6=Sun)
        -- model_id: NULL = use the currently-active model at runtime
        -- use_custom_notify_classes: 0 = global detection_class.notification_enabled,
        --                            1 = schedule_notification_class rows
        CREATE TABLE IF NOT EXISTS schedule (
            id                        INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id                  INTEGER REFERENCES computer_group(id) ON DELETE CASCADE,
            name                      TEXT    NOT NULL,
            days_of_week              TEXT    NOT NULL DEFAULT '0,1,2,3,4',
            start_time                TEXT    NOT NULL,
            end_time                  TEXT    NOT NULL,
            is_active                 INTEGER NOT NULL DEFAULT 1,
            model_id                  INTEGER REFERENCES ml_model(id) ON DELETE SET NULL,
            use_custom_notify_classes INTEGER NOT NULL DEFAULT 0,
            created_by                INTEGER REFERENCES user(id) ON DELETE SET NULL,
            created_at                TEXT    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_schedule_group ON schedule(group_id);

        -- per-schedule notification class overrides ───────────────────────────
        -- Only consulted when schedule.use_custom_notify_classes = 1.
        CREATE TABLE IF NOT EXISTS schedule_notification_class (
            schedule_id INTEGER NOT NULL REFERENCES schedule(id)        ON DELETE CASCADE,
            class_id    INTEGER NOT NULL REFERENCES detection_class(id) ON DELETE CASCADE,
            PRIMARY KEY (schedule_id, class_id)
        );
        CREATE INDEX IF NOT EXISTS idx_snc_schedule ON schedule_notification_class(schedule_id);

        -- audit log ───────────────────────────────────────────────────────────
        -- Immutable trail of every significant action performed by a user.
        CREATE TABLE IF NOT EXISTS audit_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER REFERENCES user(id) ON DELETE SET NULL,
            action     TEXT    NOT NULL,
            entity     TEXT,
            entity_id  INTEGER,
            detail     TEXT,
            created_at TEXT    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id);
        CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(created_at);
"""
