"""Two teachers sharing rooms must never share exam data, screenshots, exports or controls."""
import pytest
from backend.db import _core,schema,database as db
from backend.db.teacher_scope import bind,as_teacher
from backend.db.classroom_runs import register_run_computers
from backend.db.notifications import list_notifications,mark_all_read,notification_status
from backend.db.application_policy import save_policy
from backend.db.agent_credentials import provision_agent,authenticate_agent
from backend.db.agent_heartbeat import heartbeat
from backend.db.workstation_alarms import list_alarms,stop_alarm
from backend.db.schedule_editor_save import save_editor_schedule


@pytest.fixture
def classroom(tmp_path,monkeypatch):
    monkeypatch.setattr(_core,'DB_PATH',tmp_path/'classrooms.db');monkeypatch.setattr(schema,'DB_PATH',tmp_path/'classrooms.db')
    schema.init_db()
    admin=db.create_user('Admin','Strong-password1','admin')
    a=db.create_user('Teacher A','Strong-password1','teacher')
    b=db.create_user('Teacher B','Strong-password1','teacher')
    ga,gb=db.create_group('Room A'),db.create_group('Room B')
    pa,pb=db.upsert_computer('PC 123','10.0.0.123'),db.upsert_computer('PC 124','10.0.0.124')
    db.add_computer_to_group(pa,ga);db.add_computer_to_group(pb,gb)
    ra,rb=db.create_run(started_by=a),db.create_run(started_by=b)
    register_run_computers(ra,ga,[pa]);register_run_computers(rb,gb,[pb])
    student=db.auto_create_student('Learner')
    ea=db.insert_event(pa,[],user_id=student,run_id=ra,frame_bytes=b'own-frame')
    eb=db.insert_event(pb,[],user_id=student,run_id=rb,frame_bytes=b'other-frame')
    cls=_core._conn().execute("INSERT INTO detection_class(name,color_hex,created_at) VALUES ('Notepad','#fff','2026-11-20')").lastrowid
    _core._conn().commit()
    db.insert_notification(ea,cls);db.insert_notification(eb,cls)
    return dict(admin=admin,a=a,b=b,ga=ga,gb=gb,pa=pa,pb=pb,ra=ra,rb=rb,ea=ea,eb=eb)


def test_private_history_analytics_frames_reports_and_notifications(classroom):
    x=classroom
    with as_teacher(x['a']):
        assert [r['event_id'] for r in db.query_events()]==[x['ea']]
        assert db.count_query_events()==1
        assert db.get_summary_stats()['total_events']==1
        assert [r['id'] for r in db.list_runs()]==[x['ra']]
        assert db.get_event_frame_b64(x['eb']) is None
        assert db.get_event_frame_b64(x['ea'])
        assert [r['event_id'] for r in list_notifications()]==[x['ea']]
        mark_all_read();assert notification_status()['unread']==0
        with pytest.raises(PermissionError):db.get_run(x['rb'])
        with pytest.raises(PermissionError):db.get_run_detections(x['rb'])
        with pytest.raises(PermissionError):db.get_run_computer_summary(x['rb'])
        assert [r['id'] for r in db.list_computers()]==[x['pa']]
    assert bind(x['b'],notification_status)()['unread']==1
    assert len(db.query_events())==2


def test_alarm_latches_until_owner_stops_then_rearms_on_reopening(classroom):
    x=classroom
    token=provision_agent(x['admin'],x['pa'])
    assert authenticate_agent(token)==x['pa']
    assert authenticate_agent(provision_agent(x['admin'],x['pa']))==x['pa']
    assert authenticate_agent(token) is None
    save_policy(x['a'],'blocklist',['notepad.exe'])
    assert heartbeat(x['pa'],'notepad.exe')['alarm']
    assert heartbeat(x['pa'],'chrome.exe')['alarm']
    alarm=list_alarms(x['a'])[0]
    assert list_alarms(x['b'])==[]
    with pytest.raises(PermissionError):stop_alarm(x['b'],alarm['id'])
    assert heartbeat(x['pa'],'notepad.exe')['alarm']
    stop_alarm(x['a'],alarm['id'])
    assert not heartbeat(x['pa'],'notepad.exe')['alarm']
    assert not heartbeat(x['pa'],'chrome.exe')['alarm']
    assert heartbeat(x['pa'],'notepad.exe')['alarm']
    assert len(list_alarms(x['a']))==1
    assert heartbeat(x['pb'],'notepad.exe')['alarm'] is False
    assert _core._conn().execute('SELECT stopped_by FROM workstation_alarm WHERE id=?',(alarm['id'],)).fetchone()[0]==x['a']


def test_teacher_can_use_another_room_without_seeing_previous_teacher_records(classroom):
    x=classroom;db.finish_run(x['ra']);new=db.create_run(started_by=x['b']);register_run_computers(new,x['ga'],[x['pa']])
    save_policy(x['b'],'allowlist',['chrome.exe'])
    provision_agent(x['admin'],x['pa'])
    assert heartbeat(x['pa'],'notepad.exe')['alarm']
    assert list_alarms(x['b'])[0]['run_id']==new
    assert list_alarms(x['a'])==[]


def test_private_schedules_and_room_conflicts(classroom):
    x=classroom
    payload=dict(name='Exam',group_id=x['ga'],days=['0'],start='09:00',end='10:00',active=True,custom=False)
    sid=bind(x['a'],save_editor_schedule)(payload,x['a'])
    with as_teacher(x['b']):
        assert db.list_schedules()==[]
        with pytest.raises(PermissionError):db.get_schedule(sid)
        with pytest.raises(PermissionError):db.delete_schedule(sid)
        with pytest.raises(PermissionError):save_editor_schedule(payload,x['b'],sid)
        with pytest.raises(ValueError,match='already has an exam'):save_editor_schedule(payload,x['b'])
        sid2=save_editor_schedule(dict(payload,group_id=x['gb']),x['b'])
        assert db.get_schedule(sid2)['created_by']==x['b']


def test_scope_runs_inside_executor_and_resets_afterward(classroom):
    from concurrent.futures import ThreadPoolExecutor
    x=classroom
    with ThreadPoolExecutor(max_workers=1) as pool:
        assert pool.submit(bind(x['a'],db.count_query_events)).result()==1
        assert pool.submit(db.count_query_events).result()==2
    with pytest.raises(PermissionError):bind(x['admin'],db.count_query_events)()


def test_stop_request_stays_visible_until_workstation_acknowledges(classroom):
    x=classroom;provision_agent(x['admin'],x['pa']);save_policy(x['a'],'blocklist',['notepad.exe'])
    heartbeat(x['pa'],'notepad.exe',False)
    heartbeat(x['pa'],'notepad.exe',True)
    alarm=list_alarms(x['a'])[0];stop_alarm(x['a'],alarm['id'])
    assert list_alarms(x['a'])[0]['stopped_at']
    assert not heartbeat(x['pa'],'notepad.exe',True)['alarm']
    assert list_alarms(x['a'])
    assert not heartbeat(x['pa'],'notepad.exe',False)['alarm']
    assert list_alarms(x['a'])==[]


def test_vision_alarm_rearms_only_after_blocked_class_disappears(classroom):
    from backend.services.vision_alarms import update,_armed
    _armed.clear();x=classroom
    cls=_core._conn().execute("SELECT id FROM detection_class WHERE name='Notepad'").fetchone()[0]
    prohibited={0:{'id':cls}};dets=[{'class_id':0}]
    update(x['ea'],dets,prohibited,[0]);_core._conn().commit()
    alarm=list_alarms(x['a'])[0];stop_alarm(x['a'],alarm['id'])
    update(x['ea'],dets,prohibited,[0]);_core._conn().commit();assert list_alarms(x['a'])==[]
    update(x['ea'],[],prohibited,[]);update(x['ea'],dets,prohibited,[0]);_core._conn().commit()
    assert len(list_alarms(x['a']))==1


def test_active_exams_protect_teacher_and_classroom_from_deletion(classroom):
    x=classroom
    with pytest.raises(ValueError,match='End this teacher'):db.delete_user(x['a'])
    with pytest.raises(ValueError,match='running exam'):db.delete_group(x['ga'])
    assert db.get_user_by_id(x['a']) and db.get_group(x['ga'])


def test_process_alerts_are_searchable_and_class_filters_stay_private(classroom):
    x=classroom;provision_agent(x['admin'],x['pa']);save_policy(x['a'],'blocklist',['notepad.exe'])
    heartbeat(x['pa'],'notepad.exe')
    with as_teacher(x['a']):
        assert db.count_query_events(class_name='notepad.exe')==1
        rows=db.query_events(class_name='notepad.exe')
        assert rows[0]['detections']=='notepad.exe'
        assert 'notepad.exe' in [c['name'] for c in db.list_classes()]
    with as_teacher(x['b']):
        assert db.count_query_events(class_name='notepad.exe')==0
        assert 'notepad.exe' not in [c['name'] for c in db.list_classes()]
