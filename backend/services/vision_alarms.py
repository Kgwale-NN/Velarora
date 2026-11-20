"""Rearm a visual alarm only after the prohibited class disappears from the screen."""
from backend.db._core import _conn
from backend.db.workstation_alarms import raise_alarm
import threading

_lock=threading.Lock()
_armed={}


def update(event_id,dets,prohibited,fired):
    c=_conn()
    event=c.execute('SELECT e.run_id,e.computer_id,r.classroom_id FROM detection_event e '
        'JOIN monitoring_run r ON r.id=e.run_id WHERE e.id=?',(event_id,)).fetchone()
    if not event or event['classroom_id'] is None:
        return
    run,pc=event['run_id'],event['computer_id']
    present={d['class_id'] for d in dets if d['class_id'] in prohibited}
    with _lock:
        for key in list(_armed):
            if key[:2]==(run,pc) and key[2] not in present:
                _armed.pop(key,None)
        for cls in present:
            _armed.setdefault((run,pc,cls),True)
        for cls in fired:
            key=(run,pc,cls)
            if _armed.get(key):
                name=c.execute('SELECT name FROM detection_class WHERE id=?',(prohibited[cls]['id'],)).fetchone()
                raise_alarm(c,run,pc,event_id,name[0] if name else 'Blocked application','vision')
                _armed[key]=False
