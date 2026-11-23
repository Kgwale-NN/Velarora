"""React admin API enforces live roles, CSRF, safe fields and membership validation."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.db import _core,schema,database as db
from backend.api import admin_security as security
from backend.api.admin_routes import router


@pytest.fixture
def api(tmp_path,monkeypatch):
    monkeypatch.setattr(_core,'DB_PATH',tmp_path/'react.db');monkeypatch.setattr(schema,'DB_PATH',tmp_path/'react.db');schema.init_db()
    aid=db.create_user('Administrator','Strong-password1','admin',email='admin@example.test')
    tid=db.create_user('Teacher','Strong-password1','teacher',email='teacher@example.test')
    state={'auth':{'id':aid,'role':'admin'}}
    monkeypatch.setattr(security,'get_session_user',lambda:state.get('auth'))
    monkeypatch.setattr(security,'browser_state',lambda:state)
    app=FastAPI();app.include_router(router)
    with TestClient(app) as client:
        yield client,state,aid,tid


def headers(client):
    return {'X-CSRF-Token':client.get('/api/admin/session').json()['csrf']}


def test_failed_write_does_not_lock_other_requests_or_exam_start(api,monkeypatch):
    import sqlite3
    from backend.api import classroom_routes,staff_security
    client,state,admin,teacher=api
    client.app.include_router(classroom_routes.router)
    monkeypatch.setattr(staff_security,'get_session_user',lambda:state.get('auth'))
    monkeypatch.setattr(staff_security,'browser_state',lambda:state)
    monkeypatch.setattr(classroom_routes,'browser_state',lambda:state)
    csrf=headers(client)
    payload={'name':'Duplicate classroom'}
    created=client.post('/api/admin/classrooms',json=payload,headers=csrf)
    assert created.status_code==201
    assert client.post('/api/admin/classrooms',json=payload,headers=csrf).status_code==409
    # A separate connection catches leaked writer locks even when the executor
    # happens to reuse its original thread for the following API request.
    with sqlite3.connect(_core.DB_PATH,timeout=.2) as independent:
        independent.execute('BEGIN IMMEDIATE')
        independent.rollback()
    def start_exam(gid,owner):
        db.log_action('classroom.exam_start',user_id=owner,entity='computer_group',entity_id=gid)
        db.create_run(started_by=owner,group_name='Regression exam')
    monkeypatch.setattr(classroom_routes,'start_classroom',start_exam)
    state['auth']={'id':teacher,'role':'teacher'}
    started=client.post('/api/teacher/exam/start',json={'classroom_id':created.json()['id']},headers=csrf)
    assert started.status_code==200
    for run in db.list_runs():db.finish_run(run['id'])
    state['auth']={'id':admin,'role':'admin'}
    assert client.delete('/api/admin/users/'+str(teacher),headers=csrf).status_code==200


def test_failed_operation_rolls_back_partial_writes(api):
    from backend.api.admin_routes import _perform_transaction
    import sqlite3
    def fail():
        _core._conn().execute("INSERT INTO computer_group(name,created_at) VALUES ('Not committed','now')")
        raise ValueError('rejected')
    with pytest.raises(ValueError):_perform_transaction(fail)
    assert not _core._conn().in_transaction
    assert not _core._conn().execute("SELECT 1 FROM computer_group WHERE name='Not committed'").fetchone()
    with sqlite3.connect(_core.DB_PATH,timeout=.2) as independent:
        independent.execute('BEGIN IMMEDIATE')
        independent.rollback()


def test_database_contention_returns_a_retryable_response(api,monkeypatch):
    import sqlite3
    from backend.api import admin_service
    client,_,_,teacher=api
    csrf=headers(client)
    def busy(*args):raise sqlite3.OperationalError('database is locked')
    monkeypatch.setattr(admin_service,'delete_user',busy)
    response=client.delete('/api/admin/users/'+str(teacher),headers=csrf)
    assert response.status_code==503 and response.headers['Retry-After']=='2'
    assert db.get_user_by_id(teacher)


def test_deleting_user_keeps_large_history_and_uses_small_batches(api,monkeypatch):
    from backend.db import user_updates
    client,_,_,teacher=api
    pc=db.upsert_computer('Evidence PC','localhost')
    run=db.create_run(started_by=teacher)
    for i in range(53):
        db.insert_event(pc,[],user_id=teacher,run_id=run,frame_bytes=b'saved screenshot',os_username='Learner')
    db.finish_run(run)
    detached=[]
    original=user_updates.nullify_user_events
    def detach(uid,batch_size):
        detached.append(batch_size)
        return original(uid,batch_size)
    monkeypatch.setattr(user_updates,'nullify_user_events',detach)
    assert client.delete('/api/admin/users/'+str(teacher),headers=headers(client)).status_code==200
    assert detached==[50]
    rows=_core._conn().execute('SELECT user_id,frame_blob,os_username FROM detection_event WHERE run_id=?',(run,)).fetchall()
    assert len(rows)==53
    assert all(r['user_id'] is None and r['frame_blob']==b'saved screenshot' and r['os_username']=='Learner' for r in rows)


def test_rejects_unauthenticated_teacher_and_missing_csrf(api):
    client,state,_,tid=api
    assert client.post('/api/admin/classrooms',json={'name':'Lab A'}).status_code==403
    state['auth']={'id':tid,'role':'admin'}
    assert client.get('/api/admin/users').status_code==403
    state.clear();assert client.get('/api/admin/users').status_code==401


def test_creates_only_teachers_and_never_exposes_password_hashes(api):
    client,_,aid,_=api;csrf=headers(client)
    response=client.get('/api/admin/users');assert response.headers['cache-control']=='no-store'
    assert all('hashed_password' not in u for u in response.json())
    payload={'username':'New Teacher','email':'new@example.test','password':'Strong-password1'}
    assert client.post('/api/admin/users',json=dict(payload,role='admin'),headers=csrf).status_code==422
    created=client.post('/api/admin/users',json=payload,headers=csrf);assert created.status_code==201
    assert db.get_user_by_id(created.json()['id'])['role']=='teacher'
    assert client.post('/api/admin/users',json=payload,headers=csrf).status_code==409
    assert client.delete('/api/admin/users/'+str(aid),headers=csrf).status_code==400
    assert client.delete('/api/admin/users/'+str(created.json()['id']),headers=csrf).status_code==200


def test_classroom_assignment_validates_and_replaces_atomically(api):
    client,_,_,_=api;csrf=headers(client)
    gid=client.post('/api/admin/classrooms',json={'name':'Lab A'},headers=csrf).json()['id']
    pc=db.upsert_computer('PC 123','localhost')
    url=f'/api/admin/classrooms/{gid}/members'
    assert client.put(url,json={'computer_ids':[pc]},headers=csrf).status_code==200
    assert client.put(url,json={'computer_ids':[pc,9999]},headers=csrf).status_code==400
    assert client.get(url).json()==[pc]
    assert client.put('/api/admin/classrooms/'+str(gid),json={'name':'Lab B','description':'New name'},headers=csrf).status_code==200
    assert client.get('/api/admin/classrooms').json()['classrooms'][0]['name']=='Lab B'
    assert client.delete('/api/admin/classrooms/'+str(gid),headers=csrf).status_code==200
    assert db.list_computers()[0]['id']==pc


def test_inactive_admin_is_denied_even_with_an_old_session(api):
    client,_,aid,_=api;csrf=headers(client)
    with _core._conn() as c:c.execute('UPDATE user SET is_active=0 WHERE id=?',(aid,))
    assert client.get('/api/admin/users').status_code==403
    assert client.post('/api/admin/classrooms',json={'name':'Denied'},headers=csrf).status_code==403
