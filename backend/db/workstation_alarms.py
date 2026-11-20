"""Latched alarms survive app closure and end only through an owning teacher's command."""
from backend.db._core import _conn,_now
from backend.db.audit import _insert_audit
from backend.db.teacher_scope import as_teacher


def raise_alarm(c,run_id,computer_id,event_id,app_name,source='application'):
    inserted=c.execute('INSERT OR IGNORE INTO workstation_alarm(run_id,computer_id,event_id,app_name,source,created_at) VALUES (?,?,?,?,?,?)',
              (run_id,computer_id,event_id,app_name,source,_now()))
    if inserted.rowcount:
        _insert_audit(c,'alarm.start',entity='workstation_alarm',entity_id=inserted.lastrowid,detail=f'run={run_id}, source={source}, app={app_name}')


def list_alarms(teacher_id):
    with as_teacher(teacher_id):
        return [dict(r) for r in _conn().execute('SELECT a.*,c.name AS computer,g.name AS classroom,ca.last_seen,ca.audio_active '
            'FROM workstation_alarm a JOIN monitoring_run r ON r.id=a.run_id JOIN computer c ON c.id=a.computer_id '
            'LEFT JOIN computer_group g ON g.id=r.classroom_id LEFT JOIN computer_agent ca ON ca.computer_id=c.id '
            'WHERE r.started_by=? AND (a.stopped_at IS NULL OR (ca.audio_active=1 AND a.id='
            '(SELECT MAX(latest.id) FROM workstation_alarm latest WHERE latest.computer_id=a.computer_id))) ORDER BY a.id DESC',(teacher_id,))]


def stop_alarm(teacher_id,alarm_id):
    with as_teacher(teacher_id),_conn() as c:
        result=c.execute('UPDATE workstation_alarm SET stopped_at=?,stopped_by=? WHERE id=? AND stopped_at IS NULL '
            'AND run_id IN (SELECT id FROM monitoring_run WHERE started_by=?)',(_now(),teacher_id,alarm_id,teacher_id))
        if not result.rowcount:
            raise PermissionError('This alarm is already stopped or belongs to another teacher.')
        _insert_audit(c,'alarm.stop',user_id=teacher_id,entity='workstation_alarm',entity_id=alarm_id)
