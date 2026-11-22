"""Register a separately named outbound PC without changing existing Veyon machines."""
import uuid
from backend.db._core import _conn, _now
from backend.db.audit import _insert_audit


def register(admin_id, name, classroom_id):
    name = name.strip()
    if not name or len(name) > 100:
        raise ValueError('Enter a PC name of at most 100 characters.')
    c = _conn()
    with c:
        c.execute('BEGIN IMMEDIATE')
        if not c.execute("SELECT 1 FROM user u JOIN role r ON r.id=u.role_id WHERE u.id=? "
                         "AND u.is_active=1 AND r.name='admin'", (admin_id,)).fetchone():
            raise PermissionError('Administrator access is required.')
        if not c.execute('SELECT 1 FROM computer_group WHERE id=?', (classroom_id,)).fetchone():
            raise ValueError('Choose an existing classroom.')
        pc = c.execute('INSERT INTO computer(name,host_address,created_at) VALUES (?,?,?) RETURNING id',
                       (name, 'agent:' + uuid.uuid4().hex, _now())).fetchone()[0]
        c.execute('INSERT INTO computer_group_member(computer_id,group_id) VALUES (?,?)', (pc, classroom_id))
        _insert_audit(c, 'computer.register_agent', user_id=admin_id, entity='computer', entity_id=pc)
    return {'id': pc}
