"""SQL table definitions; loaded by schema.init_db."""
SQL = """

        -- ml models ───────────────────────────────────────────────────────────
        -- Training config (dataset_path, base_model, epochs, batch, device)
        -- is stored directly here — no separate training_session table.
        -- Fine-tune provenance: parent_model_id, finetune_lr, finetune_frozen
        CREATE TABLE IF NOT EXISTS ml_model (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT    NOT NULL UNIQUE,
            pt_path         TEXT,
            onnx_path       TEXT,
            nc              INTEGER NOT NULL,
            classes_json    TEXT    NOT NULL,
            imgsz           INTEGER NOT NULL DEFAULT 640,
            map50           REAL,
            map50_95        REAL,
            precision       REAL,
            recall          REAL,
            is_active       INTEGER NOT NULL DEFAULT 0,
            status          TEXT    NOT NULL DEFAULT 'ready',
            dataset_path    TEXT,
            base_model      TEXT,
            epochs          INTEGER,
            batch           INTEGER,
            device          TEXT,
            parent_model_id INTEGER REFERENCES ml_model(id) ON DELETE SET NULL,
            finetune_lr     REAL,
            finetune_frozen INTEGER,
            created_at      TEXT    NOT NULL,
            finished_at     TEXT
        );

        -- model → class index mapping ─────────────────────────────────────────
        -- Maps each model's raw output class indices to detection_class rows.
        -- Kept separate so two models can assign the same class at different
        -- indices without corrupting each other's mapping.
        CREATE TABLE IF NOT EXISTS model_class (
            model_id    INTEGER NOT NULL REFERENCES ml_model(id)        ON DELETE CASCADE,
            class_index INTEGER NOT NULL,
            class_id    INTEGER NOT NULL REFERENCES detection_class(id) ON DELETE CASCADE,
            UNIQUE(model_id, class_index)
        );
        CREATE INDEX IF NOT EXISTS idx_mc_model ON model_class(model_id);
"""
