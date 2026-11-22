"""Room claiming and scheduling remain isolated under concurrent teachers."""
import pytest
from unittest.mock import MagicMock
from backend.db import _core,schema,database as db
from backend.services import classroom_monitor as manager
from backend.services.classroom_state import rooms


@pytest.fixture
def setup(tmp_path,monkeypatch):
    monkeypatch.setattr(_core,'DB_PATH',tmp_path/'runtime.db');monkeypatch.setattr(schema,'DB_PATH',tmp_path/'runtime.db');schema.init_db()
    rooms.clear()
    a=db.create_user('A','Strong-password1','teacher');b=db.create_user('B','Strong-password1','teacher')
    ga,gb=db.create_group('A'),db.create_group('B')
    pa,pb=db.upsert_computer('PC A','host-a'),db.upsert_computer('PC B','host-b')
    db.add_computer_to_group(pa,ga);db.add_computer_to_group(pb,gb)
    mid=db.create_ml_model('Fake model',1,['Notepad']);db.set_active_model(mid)
    import backend.config
    monkeypatch.setattr(backend.config,'collect_cfg',lambda:{'key_data':'test','detect_imgsz':640})
    factory=MagicMock(side_effect=lambda *a,**k:MagicMock())
    yield a,b,ga,gb,pa,pb,factory
    rooms.clear()


def test_two_classrooms_run_independently_and_one_teacher_cannot_stop_another(setup):
    a,b,ga,gb,_,_,factory=setup
    one=manager.start_classroom(ga,a,controller_factory=factory)
    two=manager.start_classroom(gb,b,controller_factory=factory)
    assert one is not two and one.owner_id==a and two.owner_id==b
    one.latest_frames['private']='private frame'
    assert not two.latest_frames
    with pytest.raises(PermissionError):manager.stop_classroom(ga,b)
    with pytest.raises(ValueError,match='already running'):manager.start_classroom(ga,b,controller_factory=factory)
    manager.stop_classroom(ga,a)
    assert two.monitor is not None and one.latest_frames=={}
    replacement=manager.start_classroom(ga,b,controller_factory=factory)
    assert replacement.owner_id==b and not replacement.latest_frames


def test_same_pc_cannot_be_claimed_by_two_rooms(setup):
    a,b,ga,gb,pa,_,factory=setup
    db.add_computer_to_group(pa,gb)
    manager.start_classroom(ga,a,controller_factory=factory)
    with pytest.raises(ValueError,match='another exam'):manager.start_classroom(gb,b,controller_factory=factory)


def test_scheduler_stops_only_expired_scheduled_rooms_and_suppresses_manual_stop(setup,monkeypatch):
    from backend.services import schedule_service
    a,b,ga,gb,_,_,factory=setup
    one=manager.start_classroom(ga,a,controller_factory=factory)
    two=manager.start_classroom(gb,b,controller_factory=factory)
    two.schedule_triggered=True;two.schedule_id=9
    monkeypatch.setattr('backend.db.schedule_timing.get_active_schedules_now',lambda:[])
    schedule_service._tick()
    assert one.monitor is not None and two.monitor is None
    two.schedule_id=9;two.suppressed_schedule=9
    monkeypatch.setattr('backend.db.schedule_timing.get_active_schedules_now',lambda:[{'id':9,'created_by':b,'group_id':gb}])
    start=MagicMock();monkeypatch.setattr(schedule_service,'start_classroom',start)
    schedule_service._tick();start.assert_not_called()


def test_bound_calls_fail_after_shared_browser_changes_teacher(setup):
    from backend.db.teacher_scope import bind
    a,b,_,_,_,_,_=setup
    session={'auth':{'id':a,'role':'teacher'}}
    read=bind(a,db.list_runs,session)
    assert read()==[]
    session['auth']={'id':b,'role':'teacher'}
    with pytest.raises(PermissionError,match='session ended'):read()


def test_slow_room_shutdown_does_not_lock_other_classroom_updates(setup):
    import threading
    from backend.services.classroom_state import registry_lock
    a,_,ga,_,_,_,factory=setup
    room=manager.start_classroom(ga,a,controller_factory=factory)
    def stopping():
        acquired=threading.Event()
        def another_room():
            with registry_lock:acquired.set()
        worker=threading.Thread(target=another_room)
        worker.start()
        assert acquired.wait(1), 'Room shutdown held the shared registry lock'
        worker.join()
        with pytest.raises(ValueError,match='already running'):
            manager.start_classroom(ga,a,controller_factory=factory)
    room.monitor.stop.side_effect=stopping
    manager.stop_classroom(ga,a)
    assert room.monitor is None and not room.stopping


def test_real_monitor_workers_record_separate_owned_runs(setup,monkeypatch):
    import time
    import numpy as np
    from backend.services.monitor_service import MonitorController,_drain_state
    from backend.services.classroom_state import ClassroomState
    from backend.core.imaging import encode_jpeg
    from backend.db.teacher_scope import as_teacher
    a,b,ga,gb,pa,pb,_=setup
    image=np.zeros((20,40,3),dtype=np.uint8);raw=encode_jpeg(image,80)
    models=[]
    class Model:
        def __init__(self,*args,**kwargs):models.append(self)
        def __call__(self,images,**kwargs):return [object() for _ in images]
    def sample(self,name,host,base):
        self.state.computer_os_usernames[name]='Learner '+name
        self._raw_q.put((name,raw,image,time.perf_counter(),'notepad.exe'))
        self._stop.wait(3)
    monkeypatch.setattr('backend.services.monitor_service.yolo.YOLO',Model)
    monkeypatch.setattr(MonitorController,'_io_worker',sample)
    monkeypatch.setattr('backend.services.monitor_service.postprocess',lambda result,image,keep:(image,[]))
    monkeypatch.setattr('backend.services.monitor_service.alert_service.check_and_fire',lambda *a,**kw:0)
    cfg={'host':'localhost','port':11080,'auto_start':False,'key_data':'test','model_path':'preview.pt',
         'detect_imgsz':640,'batch_max_cpu':1,'batch_max_cuda':1,'img_quality':80,'keep_top1':True,
         'detect_conf':.5,'detect_iou':.4,'interval':.1}
    model=db.get_active_model()['id']
    workspaces=[];controllers=[]
    try:
        for owner,gid,name,host in [(a,ga,'PC A','host-a'),(b,gb,'PC B','host-b')]:
            room=ClassroomState(gid,owner)
            mc=MonitorController(cfg,computers=[{'name':name,'host':host}],model_id=model,started_by=owner,workspace=room)
            room.monitor=mc;workspaces.append(room);controllers.append(mc);mc.start()
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            if db.count_query_events()>=2:break
            time.sleep(.05)
        assert db.count_query_events()==2
        for owner,_cid,room in zip((a,b),(pa,pb),workspaces):
            with as_teacher(owner):
                rows=db.query_events();assert len(rows)==1
                assert rows[0]['foreground_app']=='notepad.exe'
                assert db.list_runs()[0]['started_by']==owner
            _drain_state(room)
            assert len(room.latest_frames)==1
        assert len(models)==2 and models[0] is not models[1]
    finally:
        for mc in controllers:mc.stop()
    assert all(db.get_run(mc.run_id)['status']=='finished' for mc in controllers)


def test_stopped_alarm_waits_for_real_agent_silence_acknowledgement(setup):
    from backend.db.agent_heartbeat import heartbeat
    from backend.db.workstation_alarms import raise_alarm, stop_alarm
    a,_b,ga,_gb,pa,_pb,factory=setup
    rid=db.create_run(started_by=a)
    with _core._conn() as c:
        c.execute('INSERT INTO computer_agent(computer_id,token_hash,audio_active) VALUES (?,?,1)',(pa,'test-hash'))
        raise_alarm(c,rid,pa,None,'notepad.exe')
    aid=_core._conn().execute('SELECT id FROM workstation_alarm WHERE run_id=?',(rid,)).fetchone()[0]
    stop_alarm(a,aid)
    db.finish_run(rid)
    with pytest.raises(ValueError,match='PC has not confirmed silence'):
        manager.start_classroom(ga,a,controller_factory=factory)
    assert heartbeat(pa,'chrome.exe',False)['alarm'] is False
    assert manager.start_classroom(ga,a,controller_factory=factory).owner_id==a


def test_active_alarm_stays_blocked_even_if_audio_report_is_false(setup):
    from backend.db.workstation_alarms import raise_alarm
    a,_b,ga,_gb,pa,_pb,factory=setup
    rid=db.create_run(started_by=a)
    with _core._conn() as c:
        c.execute('INSERT INTO computer_agent(computer_id,token_hash,audio_active) VALUES (?,?,0)',(pa,'test-hash'))
        raise_alarm(c,rid,pa,None,'notepad.exe')
    db.finish_run(rid)
    with pytest.raises(ValueError,match='teacher must stop'):
        manager.start_classroom(ga,a,controller_factory=factory)
