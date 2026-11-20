"""All foreground applications and export rows for a teacher-owned exam."""
from backend.db._core import _conn
from backend.db.teacher_scope import require_run


def application_summary(run_id):
    require_run(run_id)
    return [dict(r) for r in _conn().execute('SELECT foreground_app AS application,COUNT(*) AS samples '
        'FROM detection_event WHERE run_id=? AND foreground_app IS NOT NULL '
        'GROUP BY foreground_app ORDER BY samples DESC,application',(run_id,))]


def run_activity(run_id):
    require_run(run_id)
    return [dict(r) for r in _conn().execute("SELECT e.detected_at,c.name AS computer,"
        "COALESCE(u.username,e.os_username,'') AS student,COALESCE(e.foreground_app,'') AS foreground_app,"
        "COALESCE(dc.name,'') AS class_name,d.confidence,d.box_x1,d.box_y1,d.box_x2,d.box_y2 "
        "FROM detection_event e JOIN computer c ON c.id=e.computer_id "
        "LEFT JOIN user u ON u.id=e.user_id LEFT JOIN detection d ON d.event_id=e.id "
        "LEFT JOIN detection_class dc ON dc.id=d.class_id WHERE e.run_id=? ORDER BY e.detected_at DESC,e.id DESC",(run_id,))]
