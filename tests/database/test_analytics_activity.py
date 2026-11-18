"""Student analytics must filter before choosing the top twenty results."""
import pytest
from backend.db import _core, schema
from backend.db.analytics_activity import get_student_activity


@pytest.fixture
def activity_db(tmp_path, monkeypatch):
    monkeypatch.setattr(_core, 'DB_PATH', tmp_path / 'analytics.db')
    monkeypatch.setattr(schema, 'DB_PATH', tmp_path / 'analytics.db')
    schema.init_db()
    c = _core._conn()
    role = c.execute("SELECT id FROM role WHERE name='student'").fetchone()[0]
    pc = c.execute("INSERT INTO computer(name,host_address,created_at) VALUES ('Lab','127.0.0.1','2026-11-18')").lastrowid
    selected = None
    for index in range(22):
        selected = c.execute('INSERT INTO user(username,hashed_password,role_id,is_active,created_at) VALUES (?,?,?,1,?)',
                             (f'Student {index}', 'unused', role, '2026-11-18')).lastrowid
        for _ in range(2 if index < 21 else 1):
            c.execute('INSERT INTO detection_event(computer_id,user_id,detected_at,had_detection) VALUES (?,?,?,1)',
                      (pc, selected, '2026-11-18 10:00:00'))
    c.commit()
    return c, pc, selected


def test_selected_student_outside_top_twenty_is_still_included(activity_db):
    _, pc, selected = activity_db
    assert 'Student 21' not in [r['student'] for r in get_student_activity(pc)]
    assert get_student_activity(pc, user_id=selected) == [{'student': 'Student 21', 'hits': 1}]


def test_student_filter_combines_with_dates_computer_and_hits_only(activity_db):
    c, pc, selected = activity_db
    other_pc = c.execute("INSERT INTO computer(name,host_address,created_at) VALUES ('Other','127.0.0.2','2026-11-18')").lastrowid
    for computer, timestamp, hit in [(other_pc, '2026-11-18 10:00:00', 1),
                                     (pc, '2026-11-17 10:00:00', 1),
                                     (pc, '2026-11-18 11:00:00', 0)]:
        c.execute('INSERT INTO detection_event(computer_id,user_id,detected_at,had_detection) VALUES (?,?,?,?)',
                  (computer, selected, timestamp, hit))
    c.commit()
    assert get_student_activity(pc, '2026-11-18', '2026-11-18', user_id=selected) == [
        {'student': 'Student 21', 'hits': 1}]
    assert get_student_activity(pc, '2026-11-19', '2026-11-19', user_id=selected) == []
