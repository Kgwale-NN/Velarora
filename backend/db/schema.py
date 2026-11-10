"""Create tables, apply migrations and seed roles without changing saved data."""
from backend.db._core import DB_PATH, _conn
from backend.db.schema_accounts import SQL as ACCOUNTS_SQL
from backend.db.schema_schedules import SQL as SCHEDULES_SQL
from backend.db.schema_events import SQL as EVENTS_SQL
from backend.db.schema_models import SQL as MODELS_SQL
from backend.db.schema_seed import (
    DEFAULT_CLASSES as DEFAULT_CLASSES, seed_classes as seed_classes,
    ensure_default_admin as ensure_default_admin,
    ensure_default_teacher as ensure_default_teacher,
)


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = _conn()
    c.executescript(ACCOUNTS_SQL + SCHEDULES_SQL + EVENTS_SQL + MODELS_SQL)
    _migrate(c)
    # Seed roles idempotently after CREATE TABLE IF NOT EXISTS
    c.executemany(
        "INSERT OR IGNORE INTO role (name) VALUES (?)",
        [("admin",), ("teacher",), ("student",)],
    )
    c.commit()


def _migrate(c) -> None:
    """
    Versioned migration steps for databases created before a schema change.
    Each step must be idempotent — init_db() runs on every startup.

    v1.2.0 — monitoring_run table + detection_event.run_id (reports feature).
    """
    event_cols = {r[1] for r in c.execute("PRAGMA table_info(detection_event)")}
    if "run_id" not in event_cols:
        c.execute(
            "ALTER TABLE detection_event ADD COLUMN run_id INTEGER "
            "REFERENCES monitoring_run(id) ON DELETE SET NULL"
        )
    # Outside the IF: on a fresh DB the column comes from CREATE TABLE above
    # and this is the only place that creates the index.
    c.execute(
        "CREATE INDEX IF NOT EXISTS idx_event_run ON detection_event(run_id)"
    )
