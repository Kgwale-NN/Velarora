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
