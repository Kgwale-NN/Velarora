"""Durable computer-to-exam binding used by authenticated workstation agents."""
from backend.db._core import _conn


def register_run_computers(run_id,room_id,computer_ids):
    with _conn() as c:
        c.execute('UPDATE monitoring_run SET classroom_id=? WHERE id=?',(room_id,run_id))
        c.executemany('INSERT OR IGNORE INTO run_computer(run_id,computer_id) VALUES (?,?)',[(run_id,cid) for cid in computer_ids])
