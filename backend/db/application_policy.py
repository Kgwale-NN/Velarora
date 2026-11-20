"""Exact Windows executable rules owned by a teacher, independent of model labels."""
import re
from backend.db._core import _conn
from backend.db.teacher_scope import as_teacher
from backend.db.audit import _insert_audit


def normalize_process(value):
    name=value.strip().lower()
    if not re.fullmatch(r'[\w(). +\-]{1,120}\.exe',name):
        raise ValueError('Enter an executable name such as notepad.exe, without a folder path.')
    return name


def get_policy(owner_id):
    row=_conn().execute('SELECT mode FROM application_policy WHERE owner_id=?',(owner_id,)).fetchone()
    rules=[r[0] for r in _conn().execute('SELECT process_name FROM application_rule WHERE owner_id=? ORDER BY process_name',(owner_id,))]
    return {'mode':row[0] if row else 'blocklist','processes':rules}


def save_policy(owner_id,mode,processes):
    if mode not in ('blocklist','allowlist'):
        raise ValueError('Choose an app policy.')
    names=sorted(set(normalize_process(p) for p in processes if p.strip()))
    if mode=='allowlist' and not names:
        raise ValueError('Add at least one allowed application before enabling an allowlist.')
    with as_teacher(owner_id),_conn() as c:
        c.execute('INSERT INTO application_policy(owner_id,mode) VALUES (?,?) ON CONFLICT(owner_id) DO UPDATE SET mode=excluded.mode',(owner_id,mode))
        c.execute('DELETE FROM application_rule WHERE owner_id=?',(owner_id,))
        c.executemany('INSERT INTO application_rule VALUES (?,?)',[(owner_id,p) for p in names])
        _insert_audit(c,'application_policy.save',user_id=owner_id,detail=mode)


def is_blocked(owner_id,process):
    policy=get_policy(owner_id)
    listed=process.lower() in policy['processes']
    return not listed if policy['mode']=='allowlist' else listed
