"""Replace a group's membership and its audit entry in one transaction."""
from backend.db._core import _conn
from backend.db.audit import _insert_audit


def set_group_computers(group_id: int, computer_ids, user_id=None):
    selected = {int(cid) for cid in computer_ids}
    c = _conn()
    with c:
        c.execute('BEGIN IMMEDIATE')
        if c.execute('SELECT 1 FROM computer_group WHERE id=?', (group_id,)).fetchone() is None:
            raise ValueError('This group no longer exists. Refresh the page and try again.')
        existing = {r[0] for r in c.execute('SELECT computer_id FROM computer_group_member WHERE group_id=?', (group_id,))}
        known = {r[0] for r in c.execute('SELECT id FROM computer')}
        if not selected.issubset(known):
            raise ValueError('A selected computer is no longer available. Reopen the computer list and try again.')
        added, removed = selected - existing, existing - selected
        c.executemany('DELETE FROM computer_group_member WHERE group_id=? AND computer_id=?',
                      [(group_id, cid) for cid in removed])
        c.executemany('INSERT INTO computer_group_member(group_id,computer_id) VALUES (?,?)',
                      [(group_id, cid) for cid in added])
        _insert_audit(c, 'group.assign', user_id=user_id, entity='computer_group', entity_id=group_id,
                      detail=f'+{len(added)}/-{len(removed)} computers')
    return len(added), len(removed)
