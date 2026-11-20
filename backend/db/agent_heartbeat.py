"""Authenticated workstation samples use server-owned exam/teacher IDs, never client-supplied IDs."""
from backend.db._core import _conn,_now
from backend.db.application_policy import normalize_process,is_blocked
from backend.db.workstation_alarms import raise_alarm


def heartbeat(computer_id,process,alarm_active=None):
    process=normalize_process(process) if process else ''
    c=_conn()
    with c:
        c.execute('BEGIN IMMEDIATE')
        if alarm_active is not None:
            c.execute('UPDATE computer_agent SET audio_active=? WHERE computer_id=?',(int(alarm_active),computer_id))
        previous=c.execute('SELECT last_app,last_run_id FROM computer_agent WHERE computer_id=?',(computer_id,)).fetchone()
        run=c.execute("SELECT r.* FROM monitoring_run r JOIN run_computer rc ON rc.run_id=r.id "
            "JOIN user u ON u.id=r.started_by JOIN role role ON role.id=u.role_id "
            "WHERE rc.computer_id=? AND r.status='running' AND u.is_active=1 AND role.name='teacher' "
            "ORDER BY r.id DESC LIMIT 1",(computer_id,)).fetchone()
        active=c.execute('SELECT id FROM workstation_alarm WHERE computer_id=? AND stopped_at IS NULL',(computer_id,)).fetchone()
        same=bool(previous and run and previous['last_app']==process and previous['last_run_id']==run['id'])
        event=None
        if run and process and not same:
            identity=c.execute('SELECT user_id,os_username FROM detection_event WHERE run_id=? AND computer_id=? '
                'AND os_username IS NOT NULL ORDER BY id DESC LIMIT 1',(run['id'],computer_id)).fetchone()
            event=c.execute('INSERT INTO detection_event(computer_id,run_id,user_id,os_username,detected_at,had_detection,foreground_app) VALUES (?,?,?,?,?,0,?)',
                (computer_id,run['id'],identity['user_id'] if identity else None,identity['os_username'] if identity else None,_now(),process)).lastrowid

        if run and process and not active and is_blocked(run['started_by'],process):
            stopped=c.execute('SELECT id FROM workstation_alarm WHERE run_id=? AND computer_id=? AND app_name=? AND stopped_at IS NOT NULL ORDER BY id DESC LIMIT 1',
                              (run['id'],computer_id,process)).fetchone()
            if not (stopped and same):
                if event is None:
                    event=c.execute('INSERT INTO detection_event(computer_id,run_id,detected_at,had_detection,foreground_app) VALUES (?,?,?,1,?)',
                        (computer_id,run['id'],_now(),process)).lastrowid
                else:
                    c.execute('UPDATE detection_event SET had_detection=1 WHERE id=?',(event,))
                c.execute("INSERT OR IGNORE INTO detection_class(name,color_hex,created_at) VALUES (?,'#dddddd',?)",(process,_now()))
                cls=c.execute('SELECT id FROM detection_class WHERE name=?',(process,)).fetchone()[0]
                c.execute('INSERT INTO notification(event_id,class_id,created_at) VALUES (?,?,?)',(event,cls,_now()))
                raise_alarm(c,run['id'],computer_id,event,process)
        c.execute('UPDATE computer_agent SET last_seen=?,last_app=?,last_run_id=? WHERE computer_id=?',
                  (_now(),process,run['id'] if run else None,computer_id))
        alarm=c.execute('SELECT id,app_name FROM workstation_alarm WHERE computer_id=? AND stopped_at IS NULL',(computer_id,)).fetchone()
    return {'alarm':bool(alarm),'alarm_id':alarm['id'] if alarm else None,'application':alarm['app_name'] if alarm else None,
            'exam_active':bool(run),'poll_seconds':1}
