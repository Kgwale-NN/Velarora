"""Browser screenshots and alarms require teacher ownership, CSRF and a live exam."""
import base64
import io
from types import SimpleNamespace
import pytest
from PIL import Image
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.db import _core, schema, database as db
from backend.db.teacher_scope import as_teacher
from backend.api import browser_routes, admin_security, staff_security
from backend.services import browser_monitor as monitor


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setattr(_core, 'DB_PATH', tmp_path / 'browser.db')
    monkeypatch.setattr(schema, 'DB_PATH', tmp_path / 'browser.db')
    schema.init_db()
    first = db.create_user('First', 'Secure-password1', 'teacher')
    second = db.create_user('Second', 'Secure-password1', 'teacher')
    admin = db.create_user('Admin', 'Secure-password1', 'admin')
    mid = db.create_ml_model('Test ONNX', 1, ['Notepad'], onnx_path='test.onnx')
    db.sync_classes_from_model(mid)
    db.set_active_model(mid)
    cid = _core._conn().execute("SELECT id FROM detection_class WHERE name='Notepad'").fetchone()[0]
    db.set_alert_rule(cid, True)
    state = {'auth': {'id': first, 'role': 'teacher'}, 'admin_csrf': 'test-only'}
    monkeypatch.setattr(staff_security, 'get_session_user', lambda: state.get('auth'))
    monkeypatch.setattr(staff_security, 'browser_state', lambda: state)
    monkeypatch.setattr(admin_security, 'browser_state', lambda: state)
    monkeypatch.setattr(browser_routes, 'get_settings', lambda: {'detect_conf': .5, 'detect_iou': .4, 'alert_threshold': 1})
    monkeypatch.setattr(monitor.vision, 'model_session', lambda model: object())
    detections = [{'class_id': 0, 'name': 'Notepad', 'conf': .95, 'box': [1, 1, 8, 8]}]
    monkeypatch.setattr(monitor.vision, 'predict', lambda *args: list(detections))
    monkeypatch.setattr(monitor, 'last_frame', 0)
    buffer = io.BytesIO()
    Image.new('RGB', (16, 10), 'white').save(buffer, 'JPEG')
    payload = {'jpeg': base64.b64encode(buffer.getvalue()).decode()}
    app = FastAPI()
    app.include_router(browser_routes.router)
    with TestClient(app) as client:
        yield SimpleNamespace(c=client, state=state, first=first, second=second, admin=admin,
                              payload=payload, headers={'X-CSRF-Token': 'test-only'},
                              detections=detections, cid=cid)


def test_authentication_csrf_and_admin_cannot_start_teacher_demo(api):
    assert api.c.post('/api/teacher/browser/start').status_code == 403
    api.state['auth'] = {'id': api.admin, 'role': 'admin'}
    assert api.c.post('/api/teacher/browser/start', headers=api.headers).status_code == 403
    api.state.pop('auth')
    assert api.c.post('/api/teacher/browser/start', headers=api.headers).status_code == 401


def test_screen_alarm_rearm_history_privacy_and_stop(api, monkeypatch):
    c, headers = api.c, api.headers
    opened = c.post('/api/teacher/browser/start', headers=headers).json()
    base = '/api/teacher/browser/' + opened['id']
    def frame():
        monkeypatch.setattr(monitor, 'last_frame', 0)
        return c.post(base + '/frame', json=api.payload, headers=headers)
    assert frame().json()['alarm'] is True
    api.state['auth'] = {'id': api.second, 'role': 'teacher'}
    for action in ('stop', 'stop-alarm'):
        assert c.post(base + '/' + action, headers=headers).status_code == 400
    assert frame().status_code == 400
    assert c.post('/api/teacher/browser/start', headers=headers).status_code == 400
    with as_teacher(api.second):
        assert db.count_query_events() == 0
    api.state['auth'] = {'id': api.first, 'role': 'teacher'}
    assert c.post(base + '/stop-alarm', headers=headers).status_code == 200
    assert frame().json()['alarm'] is False  # same visible app does not retrigger
    api.detections.clear()
    assert frame().json()['alarm'] is False
    api.detections.append({'class_id': 0, 'name': 'Notepad', 'conf': .9, 'box': [1, 1, 8, 8]})
    assert frame().json()['alarm'] is True
    with as_teacher(api.first):
        assert db.count_query_events() == 4
        assert db.list_runs()[0]['id'] == opened['run_id']
    assert c.post(base + '/stop', headers=headers).status_code == 200
    assert frame().status_code == 400
    assert _core._conn().execute('SELECT status FROM monitoring_run WHERE id=?', (opened['run_id'],)).fetchone()[0] == 'finished'


def test_disabled_alert_rule_records_detection_without_sounding(api, monkeypatch):
    db.set_alert_rule(api.cid, False)
    sid = api.c.post('/api/teacher/browser/start', headers=api.headers).json()['id']
    result = api.c.post(f'/api/teacher/browser/{sid}/frame', json=api.payload, headers=api.headers)
    assert result.status_code == 200
    assert len(result.json()['detections']) == 1 and not result.json()['alarm']
    assert api.c.post(f'/api/teacher/browser/{sid}/frame', json={'jpeg': 'invalid-capture'}, headers=api.headers).status_code == 400


def test_cloud_snapshot_uses_no_opencv(api, monkeypatch):
    monkeypatch.setenv('VELARORA_CLOUD_DEMO', 'true')
    sid = api.c.post('/api/teacher/browser/start', headers=api.headers).json()['id']
    response = api.c.post(f'/api/teacher/browser/{sid}/frame', json=api.payload, headers=api.headers)
    with as_teacher(api.first):
        annotated = db.get_event_frame_annotated_b64(response.json()['event_id'])
    assert annotated.startswith('data:image/jpeg;base64,')


def test_consecutive_threshold_resets_and_top_detection_is_kept(api, monkeypatch):
    monkeypatch.setattr(browser_routes, 'get_settings', lambda: {
        'detect_conf': .5, 'detect_iou': .4, 'alert_threshold': 2, 'keep_top1': True})
    sid = api.c.post('/api/teacher/browser/start', headers=api.headers).json()['id']
    url = f'/api/teacher/browser/{sid}/frame'
    def sample():
        monkeypatch.setattr(monitor, 'last_frame', 0)
        return api.c.post(url, json=api.payload, headers=api.headers).json()
    detection = dict(api.detections[0])
    api.detections.append({**detection, 'conf': .6})
    first = sample()
    assert not first['alarm'] and len(first['detections']) == 1
    api.detections.clear()
    assert not sample()['alarm']
    api.detections.append(detection)
    assert not sample()['alarm']
    assert sample()['alarm']
