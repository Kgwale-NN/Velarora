"""Classroom exam membership, workstation credentials and persistent alarm state."""
SQL="""
CREATE TABLE IF NOT EXISTS run_computer (
 run_id INTEGER NOT NULL REFERENCES monitoring_run(id) ON DELETE CASCADE,
 computer_id INTEGER NOT NULL REFERENCES computer(id) ON DELETE CASCADE,
 PRIMARY KEY(run_id,computer_id));
CREATE INDEX IF NOT EXISTS idx_run_pc ON run_computer(computer_id,run_id);
CREATE TABLE IF NOT EXISTS computer_agent (
 computer_id INTEGER PRIMARY KEY REFERENCES computer(id) ON DELETE CASCADE,
 token_hash TEXT NOT NULL UNIQUE, last_seen TEXT, last_app TEXT, last_run_id INTEGER,
 enabled INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS application_policy (
 owner_id INTEGER PRIMARY KEY REFERENCES user(id) ON DELETE CASCADE,
 mode TEXT NOT NULL DEFAULT 'blocklist' CHECK(mode IN ('blocklist','allowlist')));
CREATE TABLE IF NOT EXISTS application_rule (
 owner_id INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
 process_name TEXT NOT NULL COLLATE NOCASE, PRIMARY KEY(owner_id,process_name));
CREATE TABLE IF NOT EXISTS workstation_alarm (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 run_id INTEGER NOT NULL REFERENCES monitoring_run(id) ON DELETE CASCADE,
 computer_id INTEGER NOT NULL REFERENCES computer(id) ON DELETE CASCADE,
 event_id INTEGER REFERENCES detection_event(id) ON DELETE SET NULL,
 app_name TEXT NOT NULL, source TEXT NOT NULL DEFAULT 'application',
 created_at TEXT NOT NULL, stopped_at TEXT,
 stopped_by INTEGER REFERENCES user(id) ON DELETE SET NULL);
CREATE UNIQUE INDEX IF NOT EXISTS idx_alarm_one_active ON workstation_alarm(computer_id) WHERE stopped_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_alarm_run ON workstation_alarm(run_id);
"""


def migrate(c):
    if 'classroom_id' not in {r[1] for r in c.execute('PRAGMA table_info(monitoring_run)')}:
        c.execute('ALTER TABLE monitoring_run ADD COLUMN classroom_id INTEGER REFERENCES computer_group(id) ON DELETE SET NULL')
    c.execute('CREATE INDEX IF NOT EXISTS idx_run_teacher ON monitoring_run(started_by,id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_schedule_teacher ON schedule(created_by,id)')
    c.executescript(SQL)
    if "audio_active" not in {r[1] for r in c.execute("PRAGMA table_info(computer_agent)")}:
        c.execute("ALTER TABLE computer_agent ADD COLUMN audio_active INTEGER NOT NULL DEFAULT 0")
    c.commit()
