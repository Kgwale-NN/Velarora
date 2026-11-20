"""Per-PC revocable credentials: only a digest is stored in the server database."""
import hashlib
import secrets
from backend.db._core import _conn
from backend.db.audit import _insert_audit


def provision_agent(admin_id,computer_id):
    token=secrets.token_urlsafe(48)
    c=_conn()
    if not c.execute("SELECT 1 FROM user u JOIN role r ON r.id=u.role_id WHERE u.id=? AND u.is_active=1 AND r.name='admin'",(admin_id,)).fetchone():
        raise PermissionError('Only an administrator can provision a workstation.')
    if not c.execute('SELECT 1 FROM computer WHERE id=?',(computer_id,)).fetchone():
        raise ValueError('Select a registered computer.')
    if c.execute('SELECT 1 FROM workstation_alarm a LEFT JOIN computer_agent ca ON ca.computer_id=a.computer_id '
        'WHERE a.computer_id=? AND (a.stopped_at IS NULL OR ca.audio_active=1) LIMIT 1',(computer_id,)).fetchone():
        raise ValueError('Stop and acknowledge this PC’s alarm before rotating its agent key.')
    with c:
        c.execute('INSERT INTO computer_agent(computer_id,token_hash) VALUES (?,?) ON CONFLICT(computer_id) DO UPDATE SET token_hash=excluded.token_hash,enabled=1',
                  (computer_id,hashlib.sha256(token.encode()).hexdigest()))
        _insert_audit(c,'agent.provision',user_id=admin_id,entity='computer',entity_id=computer_id)
    return token


def authenticate_agent(token):
    if not token or len(token)>256:
        return None
    row=_conn().execute('SELECT computer_id FROM computer_agent WHERE token_hash=? AND enabled=1',
        (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
    return row['computer_id'] if row else None
