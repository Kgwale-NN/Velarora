"""Owner-scoped browser demo sessions; screens remain ordinary exam records."""
import time
import uuid
from backend.db._core import _conn
from backend.db.run_lifecycle import create_run, finish_run
from backend.db.computers import upsert_computer

SQL = """CREATE TABLE IF NOT EXISTS browser_session (
 id TEXT PRIMARY KEY, owner_id INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
 run_id INTEGER NOT NULL REFERENCES monitoring_run(id) ON DELETE CASCADE,
 computer_id INTEGER NOT NULL REFERENCES computer(id),
 model_id INTEGER REFERENCES ml_model(id) ON DELETE SET NULL,
 last_seen REAL NOT NULL, alarm INTEGER NOT NULL DEFAULT 0,
 armed INTEGER NOT NULL DEFAULT 1, hits TEXT NOT NULL DEFAULT '{}',
 notification_at REAL NOT NULL DEFAULT 0);
"""


def read(session_id, owner):
    row = _conn().execute("SELECT b.*,r.status FROM browser_session b JOIN monitoring_run r "
        "ON r.id=b.run_id WHERE b.id=? AND b.owner_id=?", (session_id, owner)).fetchone()
    if not row:
        raise PermissionError("This screen-sharing session does not belong to you.")
    return dict(row)


def begin(owner, model_id):
    c = _conn()
    now = time.time()
    for row in c.execute("SELECT b.* FROM browser_session b JOIN monitoring_run r ON r.id=b.run_id "
                         "WHERE r.status='running'").fetchall():
        if row['last_seen'] < now - 120 or row['owner_id'] == owner:
            finish_run(row['run_id'], 'interrupted')
            c.execute('UPDATE browser_session SET alarm=0 WHERE id=?', (row['id'],))
        else:
            raise ValueError("The free demo is already processing another teacher's shared screen. Try again when it ends.")
    sid = uuid.uuid4().hex
    pc = upsert_computer(f"Shared screen · teacher {owner}", f"browser:{owner}")
    run = create_run(group_name="Browser screen-sharing demo", model_id=model_id, started_by=owner)
    c.execute("INSERT INTO browser_session(id,owner_id,run_id,computer_id,model_id,last_seen) "
              "VALUES (?,?,?,?,?,?)", (sid, owner, run, pc, model_id, now))
    c.execute("INSERT INTO run_computer(run_id,computer_id) VALUES (?,?)", (run, pc))
    c.commit()
    return {"id": sid, "run_id": run}


def end(session_id, owner):
    row = read(session_id, owner)
    finish_run(row['run_id'])
    with _conn() as c:
        c.execute("UPDATE browser_session SET alarm=0 WHERE id=?", (session_id,))
    return {"ok": True}


def silence(session_id, owner):
    read(session_id, owner)
    with _conn() as c:
        c.execute("UPDATE browser_session SET alarm=0,armed=0 WHERE id=?", (session_id,))
    return {"alarm": False}
