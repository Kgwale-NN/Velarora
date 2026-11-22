"""Outbound screens are authenticated and bound to the PC's actual teacher exam."""
from io import BytesIO
import time
import pytest
from PIL import Image
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.db import _core, schema, database as db
from backend.db.agent_registration import register
from backend.db.agent_credentials import provision_agent
from backend.db.classroom_runs import register_run_computers
from backend.db.agent_capture import assignment
from backend.core import agent_api, agent_frames


@pytest.fixture
def setup(tmp_path,monkeypatch):
    path=tmp_path/'capture.db'
    monkeypatch.setattr(_core,'DB_PATH',path)
    monkeypatch.setattr(schema,'DB_PATH',path)
    schema.init_db()
    admin=db.create_user('Admin','Strong-password1','admin')
    teacher=db.create_user('Teacher','Strong-password1','teacher')
    other=db.create_user('Other','Strong-password1','teacher')
    room=db.create_group('Campus')
    pc=register(admin,'Campus PC',room)['id']
    second=register(admin,'Another PC',room)['id']
    token=provision_agent(admin,pc)
    token2=provision_agent(admin,second)
    rid=db.create_run(started_by=teacher)
    register_run_computers(rid,room,[pc])
    image=BytesIO();Image.new('RGB',(60,40),'white').save(image,'JPEG')
    async def direct(function,*args):
        return function(*args)
    monkeypatch.setattr(agent_api.run,'io_bound',direct)
    app=FastAPI();app.include_router(agent_api.router)
    with TestClient(app) as client:
        yield client,admin,teacher,other,room,pc,rid,token,token2,image.getvalue()
    agent_frames.clear_run(rid)


def test_auth_assignment_validation_and_no_previous_exam_replay(setup):
    client,_,_,_,_,pc,rid,token,token2,image=setup
    url='/api/workstation/frame'
    headers={'Authorization':'Bearer '+token,'X-Velarora-Run':str(rid),
             'X-Velarora-Process':'notepad.exe','X-Velarora-User':'Campus%20Learner'}
    assert client.post(url,content=image,headers={'X-Velarora-Run':str(rid)}).status_code==401
    assert client.post(url,content=image,headers={**headers,'Authorization':'Bearer '+token2}).status_code==409
    assert client.post(url,content=b'x'*700001,headers=headers).status_code==413
    assert client.post(url,content=b'not a picture',headers=headers).status_code==422
    assert client.post(url,content=image,headers=headers).status_code==200
    frame=agent_frames.latest(pc,rid)
    assert frame.process=='notepad.exe' and frame.username=='Campus Learner'
    assert agent_frames.latest(pc,rid,frame.sequence) is None
    assert agent_frames.latest(pc,rid+1) is None
    db.finish_run(rid)
    assert assignment(pc) is None
    assert client.post(url,content=image,headers=headers).status_code==409
    heartbeat=client.post('/api/workstation/heartbeat',json={'capture_capable':True},headers=headers).json()
    assert heartbeat['capture_allowed'] is False


def test_only_admin_registers_and_legacy_veyon_is_not_switched(setup):
    _,admin,teacher,_,room,pc,rid,_,_,_=setup
    with pytest.raises(PermissionError):register(teacher,'Forbidden',room)
    old=db.upsert_computer('Local Test','127.0.0.1')
    provision_agent(admin,old)
    register_run_computers(rid,room,[old])
    assert assignment(old) is None
    assert assignment(pc)==rid
    assert db.list_computers_in_group(room)[0]['host_address'].startswith('agent:')


def test_app_alarm_is_teacher_owned_and_stops_only_after_command(setup):
    client,_,teacher,other,_,pc,rid,token,_,_=setup
    from backend.db.application_policy import save_policy
    from backend.db.workstation_alarms import list_alarms,stop_alarm
    save_policy(teacher,'blocklist',['notepad.exe'])
    headers={'Authorization':'Bearer '+token}
    def sample(process,playing=False):
        return client.post('/api/workstation/heartbeat',headers=headers,
                           json={'process':process,'alarm_active':playing,'capture_capable':True}).json()
    assert sample('chrome.exe')['alarm'] is False
    raised=sample('notepad.exe')
    assert raised['alarm'] and raised['capture_run_id']==rid
    assert list_alarms(other)==[]
    with pytest.raises(PermissionError):stop_alarm(other,raised['alarm_id'])
    assert sample('chrome.exe',True)['alarm'] is True
    stop_alarm(teacher,raised['alarm_id'])
    assert sample('chrome.exe',True)['alarm'] is False
    sample('chrome.exe',False)
    assert list_alarms(teacher)==[]


def test_mailbox_is_bounded_expires_and_clears_run(monkeypatch):
    monkeypatch.setattr(agent_frames,'MAX_BYTES',10)
    monkeypatch.setattr(agent_frames,'_frames',{})
    clock=[time.perf_counter()]
    monkeypatch.setattr(agent_frames.time,'perf_counter',lambda:clock[0])
    agent_frames.put(1,100,b'123456','','')
    agent_frames.put(2,200,b'abcdef','','')
    assert agent_frames.latest(1,100) is None
    assert agent_frames.latest(2,200)
    clock[0]+=13
    assert agent_frames.latest(2,200) is None
    agent_frames.put(2,200,b'a','','')
    agent_frames.clear_run(200)
    assert agent_frames.latest(2,200) is None


def test_real_monitor_uses_uploaded_pc_screen_without_veyon(setup,monkeypatch):
    from backend.services.monitor_service import MonitorController,_drain_state
    from backend.services.classroom_state import ClassroomState
    from backend.db.teacher_scope import as_teacher
    from backend.services.agent_capture import accept
    from unittest.mock import MagicMock
    _,_,teacher,other,room_id,pc,old_run,_,_,image=setup
    db.finish_run(old_run)
    model=db.create_ml_model('Test model',1,['Notepad'])
    host=_core._conn().execute('SELECT host_address FROM computer WHERE id=?',(pc,)).fetchone()[0]
    fake=MagicMock(side_effect=lambda images,**kwargs:[object() for _ in images])
    monkeypatch.setattr('backend.services.monitor_service.yolo.YOLO',lambda *a,**kw:fake)
    monkeypatch.setattr('backend.services.monitor_service.postprocess',lambda result,picture,keep:(picture,[]))
    monkeypatch.setattr('backend.services.monitor_service.alert_service.check_and_fire',lambda *a,**kw:0)
    def forbidden(*a,**kw):
        raise AssertionError('An outbound PC must never call Veyon')
    monkeypatch.setattr('backend.services.monitor_service.veyon.is_port_open',forbidden)
    monkeypatch.setattr('backend.services.monitor_service.veyon.launch_webapi_server',forbidden)
    cfg={'host':'localhost','port':11080,'auto_start':True,'key_data':'','model_path':'unused.pt',
         'detect_imgsz':640,'batch_max_cpu':1,'batch_max_cuda':1,'img_quality':80,'keep_top1':True,
         'detect_conf':.5,'detect_iou':.4,'interval':.1}
    room=ClassroomState(room_id,teacher)
    controller=MonitorController(cfg,computers=[{'name':'Campus PC','host':host}],model_id=model,
                                 started_by=teacher,workspace=room)
    room.monitor=controller
    try:
        controller.start()
        deadline=time.monotonic()+8
        while assignment(pc) is None and time.monotonic()<deadline:
            time.sleep(.05)
        assert assignment(pc)==controller.run_id
        accept(pc,controller.run_id,image,'notepad.exe','Campus Learner')
        while time.monotonic()<deadline:
            with as_teacher(teacher):
                events=db.query_events()
            if events:
                break
            time.sleep(.05)
        assert len(events)==1
        assert _core._conn().execute('SELECT computer_id FROM detection_event WHERE run_id=?',
                                     (controller.run_id,)).fetchone()[0]==pc
        assert events[0]['foreground_app']=='notepad.exe'
        assert _core._conn().execute('SELECT os_username FROM detection_event WHERE run_id=?',
                                     (controller.run_id,)).fetchone()[0]=='Campus Learner'
        with as_teacher(other):
            assert db.query_events()==[]
        _drain_state(room)
        assert list(room.latest_frames)==['Campus PC']
    finally:
        controller.stop()
    assert assignment(pc) is None
    assert agent_frames.latest(pc,controller.run_id) is None


def test_campus_setup_api_requires_admin_and_csrf(setup,monkeypatch):
    from backend.api import admin_security as security
    from backend.api.admin_routes import router as admin_router
    from backend.api.management_routes import router as management_router
    _,admin,teacher,_,room,_,_,_,_,_=setup
    state={'auth':{'id':admin,'role':'admin'}}
    monkeypatch.setattr(security,'get_session_user',lambda:state.get('auth'))
    monkeypatch.setattr(security,'browser_state',lambda:state)
    app=FastAPI();app.include_router(admin_router);app.include_router(management_router)
    with TestClient(app) as client:
        payload={'name':'New Campus PC','classroom_id':room}
        assert client.post('/api/admin/workstations/computers',json=payload).status_code==403
        headers={'X-CSRF-Token':client.get('/api/admin/session').json()['csrf']}
        added=client.post('/api/admin/workstations/computers',json=payload,headers=headers)
        assert added.status_code==201
        config=client.post('/api/admin/workstations/provision',headers=headers,
            json={'computer_id':added.json()['id'],'server_url':'https://school.example'}).json()
        assert config['screen_capture'] is True and config['computer_name']=='New Campus PC'
        state['auth']={'id':teacher,'role':'admin'}
        assert client.post('/api/admin/workstations/computers',json=payload,headers=headers).status_code==403
