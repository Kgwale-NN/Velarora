"""SQL table definitions; loaded by schema.init_db."""
SQL = """

        -- detection classes ───────────────────────────────────────────────────
        -- class_index is intentionally absent: it is model-specific and lives in
        -- model_class instead, so two models can share a class name at different
        -- indices without corrupting each other's mapping.
        CREATE TABLE IF NOT EXISTS detection_class (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            name                  TEXT    NOT NULL UNIQUE,
            color_hex             TEXT    NOT NULL,
            notification_enabled  INTEGER NOT NULL DEFAULT 0,
            created_at            TEXT    NOT NULL
        );

        -- monitoring runs ─────────────────────────────────────────────────────
        -- One row per monitoring session (manual Start/Stop or scheduler-driven).
        -- trigger_type: 'manual' | 'schedule'
        -- group_name:   denormalised label ('' = all computers) so the report
        --               survives later group renames/deletions.
        -- status:       'running' | 'finished' | 'interrupted' (process died
        --               before stop — repaired by finish_stale_runs() on boot)
        CREATE TABLE IF NOT EXISTS monitoring_run (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            trigger_type TEXT    NOT NULL DEFAULT 'manual',
            schedule_id  INTEGER REFERENCES schedule(id) ON DELETE SET NULL,
            group_name   TEXT,
            model_id     INTEGER REFERENCES ml_model(id) ON DELETE SET NULL,
            started_by   INTEGER REFERENCES user(id)     ON DELETE SET NULL,
            status       TEXT    NOT NULL DEFAULT 'running',
            started_at   TEXT    NOT NULL,
            ended_at     TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_run_started ON monitoring_run(started_at);

        -- detection events ────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS detection_event (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            computer_id      INTEGER NOT NULL REFERENCES computer(id)   ON DELETE CASCADE,
            user_id          INTEGER          REFERENCES user(id)        ON DELETE SET NULL,
            model_id         INTEGER          REFERENCES ml_model(id)   ON DELETE SET NULL,
            run_id           INTEGER          REFERENCES monitoring_run(id) ON DELETE SET NULL,
            os_username      TEXT,
            detected_at      TEXT    NOT NULL,
            frame_blob       BLOB,
            had_detection    INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_event_computer  ON detection_event(computer_id);
        CREATE INDEX IF NOT EXISTS idx_event_user      ON detection_event(user_id);
        CREATE INDEX IF NOT EXISTS idx_event_model     ON detection_event(model_id);
        CREATE INDEX IF NOT EXISTS idx_event_winuser       ON detection_event(os_username);
        CREATE INDEX IF NOT EXISTS idx_event_winuser_lower ON detection_event(LOWER(os_username));
        CREATE INDEX IF NOT EXISTS idx_event_time          ON detection_event(detected_at);
        CREATE INDEX IF NOT EXISTS idx_event_comp_time ON detection_event(computer_id, detected_at);
        CREATE INDEX IF NOT EXISTS idx_event_user_time ON detection_event(user_id, detected_at);

        -- detections ──────────────────────────────────────────────────────────
        -- class_id uses RESTRICT (not CASCADE/SET NULL) so that deleting a
        -- detection_class is permanently blocked while any detection references it.
        -- To remove a class you must first delete all detection_event rows for it
        -- (which cascade-delete their detection children automatically).
        CREATE TABLE IF NOT EXISTS detection (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id   INTEGER NOT NULL REFERENCES detection_event(id) ON DELETE CASCADE,
            class_id   INTEGER NOT NULL REFERENCES detection_class(id) ON DELETE RESTRICT,
            confidence REAL    NOT NULL,
            box_x1     INTEGER NOT NULL,
            box_y1     INTEGER NOT NULL,
            box_x2     INTEGER NOT NULL,
            box_y2     INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_det_event ON detection(event_id);
        CREATE INDEX IF NOT EXISTS idx_det_class ON detection(class_id);

        -- notifications ───────────────────────────────────────────────────────
        -- computer and student are derived via event_id JOINs at query time.
        -- event_id uses CASCADE: a notification whose event is gone has no frame,
        -- computer, or student to display and should not survive its event.
        CREATE TABLE IF NOT EXISTS notification (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id   INTEGER REFERENCES detection_event(id) ON DELETE CASCADE,
            class_id   INTEGER REFERENCES detection_class(id) ON DELETE SET NULL,
            is_read    INTEGER NOT NULL DEFAULT 0,
            created_at TEXT    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_notif_read ON notification(is_read);
        CREATE INDEX IF NOT EXISTS idx_notif_time ON notification(created_at);
"""
