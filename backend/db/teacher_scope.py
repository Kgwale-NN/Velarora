"""Explicit teacher ownership carried into worker calls, never inferred from a browser filter."""
from contextvars import ContextVar
from contextlib import contextmanager
from functools import wraps
from backend.db._core import _conn

_owner = ContextVar('teacher_owner',default=None)


def owner_id():
    return _owner.get()


@contextmanager
def as_teacher(user_id):
    row=_conn().execute("SELECT 1 FROM user u JOIN role r ON r.id=u.role_id WHERE u.id=? AND u.is_active=1 AND r.name='teacher'",(user_id,)).fetchone()
    if not row:
        raise PermissionError('An active teacher account is required.')
    token=_owner.set(int(user_id))
    try:
        yield
    finally:
        _owner.reset(token)


def bind(user_id,function,session=None):
    @wraps(function)
    def call(*args,**kwargs):
        auth=session.get("auth") if session is not None else None
        if session is not None and (not auth or auth.get("id") != user_id or auth.get("role") != "teacher"):
            raise PermissionError("Your teacher session ended. Sign in again.")
        with as_teacher(user_id):
            return function(*args,**kwargs)
    return call


def event_scope(alias=''):
    prefix=alias+'.' if alias else ''
    uid=owner_id()
    return (f'{prefix}run_id IN (SELECT id FROM monitoring_run WHERE started_by=?)',[uid]) if uid is not None else ('1=1',[])


def require_run(run_id):
    uid=owner_id()
    if uid is not None and not _conn().execute('SELECT 1 FROM monitoring_run WHERE id=? AND started_by=?',(run_id,uid)).fetchone():
        raise PermissionError('This exam belongs to another teacher or has no owner.')


def require_schedule(schedule_id):
    uid=owner_id()
    if uid is not None and not _conn().execute('SELECT 1 FROM schedule WHERE id=? AND created_by=?',(schedule_id,uid)).fetchone():
        raise PermissionError('This schedule belongs to another teacher.')
