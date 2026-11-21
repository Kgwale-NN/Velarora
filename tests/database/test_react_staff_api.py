"""React API contracts: ownership, CSRF, exports and staff-only access."""

import io
import zipfile
from types import SimpleNamespace
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware
from backend.db import _core, schema, database as db
from backend.api import (
    admin_security,
    staff_security,
    auth_routes,
    teacher_routes,
    classroom_routes,
    management_routes,
    training_routes,
)


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setattr(_core, "DB_PATH", tmp_path / "staff.db")
    monkeypatch.setattr(schema, "DB_PATH", tmp_path / "staff.db")
    schema.init_db()
    aid = db.create_user("Admin", "Secure-password1", "admin", email="admin@example.test")
    first = db.create_user("First", "Secure-password1", "teacher", email="first@example.test")
    second = db.create_user("Second", "Secure-password1", "teacher", email="second@example.test")
    gid = db.create_group("Lab", "")
    pc = db.upsert_computer("PC 123", "127.0.0.1")
    db.add_computer_to_group(gid, pc)
    run = db.create_run(group_name="Lab", started_by=first)
    event = db.insert_event(pc, [], run_id=run, foreground_app="notepad.exe")
    state = {"auth": {"id": first, "role": "teacher"}, "admin_csrf": "test-csrf"}
    for module in (admin_security, staff_security, auth_routes):
        monkeypatch.setattr(module, "browser_state", lambda: state)
    for module in (admin_security, staff_security, auth_routes):
        monkeypatch.setattr(module, "get_session_user", lambda: state.get("auth"))
    monkeypatch.setattr(
        auth_routes,
        "set_session_user",
        lambda user, remember: state.update(
            auth={"id": user["id"], "role": user["role"], "username": user["username"]}
        ),
    )
    monkeypatch.setattr(auth_routes, "clear_session", lambda: state.pop("auth", None))
    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key="test-only")
    for module in (
        auth_routes,
        teacher_routes,
        classroom_routes,
        management_routes,
        training_routes,
    ):
        app.include_router(module.router)
    with TestClient(app) as client:
        yield SimpleNamespace(
            client=client,
            state=state,
            admin=aid,
            first=first,
            second=second,
            gid=gid,
            run=run,
            event=event,
            pc=pc,
            headers={"X-CSRF-Token": "test-csrf"},
        )


def test_history_reports_and_downloads_remain_private(api):
    c = api.client
    assert c.get("/api/teacher/history").json()["total"] == 1
    assert c.get("/api/teacher/analytics").json()["summary"]["total_events"] == 1
    assert c.get("/api/teacher/reports").json()[0]["id"] == api.run
    assert c.get(f"/api/teacher/reports/{api.run}/csv").content.startswith(b"\xef\xbb\xbf")
    assert c.get(f"/api/teacher/reports/{api.run}/pdf").content.startswith(b"%PDF")
    api.state["auth"] = {"id": api.second, "role": "teacher"}
    assert c.get("/api/teacher/history").json()["total"] == 0
    assert c.get("/api/teacher/reports").json() == []
    assert c.get(f"/api/teacher/reports/{api.run}").status_code == 400
    assert c.get(f"/api/teacher/reports/{api.run}/csv").status_code == 400
    assert c.get(f"/api/teacher/snapshots/{api.event}").json() == {"raw": None, "annotated": None}
    assert c.get("/api/teacher/options").json()["computers"] == []


def test_schedule_mutation_requires_csrf_and_owner(api):
    c = api.client
    payload = {
        "name": "Exam",
        "group_id": api.gid,
        "days": ["0"],
        "start": "09:00",
        "end": "10:00",
        "active": True,
    }
    assert c.post("/api/teacher/schedules", json=payload).status_code == 403
    response = c.post("/api/teacher/schedules", json=payload, headers=api.headers)
    assert response.status_code == 200, response.text
    sid = response.json()["id"]
    assert c.get("/api/teacher/schedules").json()[0]["id"] == sid
    api.state["auth"] = {"id": api.second, "role": "teacher"}
    assert c.get("/api/teacher/schedules").json() == []
    assert (
        c.put(f"/api/teacher/schedules/{sid}", json=payload, headers=api.headers).status_code == 400
    )
    assert c.delete(f"/api/teacher/schedules/{sid}", headers=api.headers).status_code == 400


def test_student_and_teacher_cannot_use_management_routes(api):
    c = api.client
    for path in ("models", "settings", "audit", "workstations", "model-alert-rules", "training"):
        assert c.get("/api/admin/" + path).status_code == 403
    api.state.clear()
    assert c.get("/api/profile").status_code == 401
    api.state["auth"] = {"id": api.admin, "role": "teacher"}
    assert c.get("/api/teacher/history").status_code == 403
    assert c.get("/api/admin/models").status_code == 200


def test_profile_login_and_password_contract(api):
    c = api.client
    response = c.get("/api/session")
    assert response.headers["cache-control"] == "no-store"
    assert "hashed_password" not in response.json()["user"]
    assert (
        c.put("/api/profile", json={"username": "Renamed"}, headers=api.headers).status_code == 200
    )
    assert api.state["auth"]["username"] == "Renamed"
    assert (
        c.put(
            "/api/profile/password",
            json={"current": "wrong", "password": "NewSecure123!"},
            headers=api.headers,
        ).status_code
        == 400
    )
    assert (
        c.put(
            "/api/profile/password",
            json={"current": "Secure-password1", "password": "NewSecure123!"},
            headers=api.headers,
        ).status_code
        == 200
    )
    api.state.pop("auth")
    response = c.post(
        "/api/login",
        json={"email": "first@example.test", "password": "NewSecure123!"},
        headers=api.headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["user"]["username"] == "Renamed"


def test_live_grid_does_not_leak_other_teacher_frames(api, monkeypatch):
    from backend.services.classroom_state import ClassroomState

    room = ClassroomState(api.gid, api.first)
    room.monitor = object()
    room.latest_frames = {"PC 123": ("annotated", "raw", [])}
    monkeypatch.setattr(classroom_routes, "rooms", {api.gid: room})
    assert api.client.get(f"/api/classrooms/{api.gid}/live").json()["frames"][0]["raw"] == "raw"
    api.state["auth"] = {"id": api.second, "role": "teacher"}
    data = api.client.get(f"/api/classrooms/{api.gid}/live").json()
    assert data["running"] and not data["owned"] and data["frames"] == [] and data["logs"] == []


def test_dataset_zip_rejects_traversal(api):
    api.state["auth"] = {"id": api.admin, "role": "admin"}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("../escape.txt", "blocked")
    response = api.client.post(
        "/api/admin/datasets/upload",
        headers=api.headers,
        files={"file": ("dataset.zip", buf.getvalue(), "application/zip")},
    )
    assert response.status_code == 400 and "unsafe" in response.text


def test_workstation_urls_and_alarm_rotation_guard(api):
    api.state["auth"] = {"id": api.admin, "role": "admin"}
    url = "/api/admin/workstations/provision"
    assert (
        api.client.post(
            url,
            json={"computer_id": api.pc, "server_url": "http://school:8080"},
            headers=api.headers,
        ).status_code
        == 400
    )
    response = api.client.post(
        url,
        json={"computer_id": api.pc, "server_url": "http://127.0.0.1:8080"},
        headers=api.headers,
    )
    assert response.status_code == 200 and len(response.json()["token"]) > 40


def test_settings_round_trip_keeps_password_and_model_managed_values(api, monkeypatch):
    import backend.config as config

    saved = []
    monkeypatch.setattr(
        config, "get_settings", lambda: {**config.DEFAULTS, "logon_password": "private-secret"}
    )
    monkeypatch.setattr(config, "save_settings", lambda value: saved.append(dict(value)))
    api.state["auth"] = {"id": api.admin, "role": "admin"}
    response = api.client.get("/api/admin/settings")
    payload = response.json()
    assert "private-secret" not in response.text and payload["logon_password"] == ""
    payload.update(model_path="must-not-change", detect_imgsz=2048)
    response = api.client.put("/api/admin/settings", json=payload, headers=api.headers)
    assert response.status_code == 200, response.text
    assert saved[0]["logon_password"] == "private-secret"
    assert saved[0]["model_path"] == config.DEFAULTS["model_path"]
    assert saved[0]["detect_imgsz"] == config.DEFAULTS["detect_imgsz"]


def test_teacher_password_reset_is_admin_only(api):
    url = f"/api/admin/users/{api.first}/password"
    payload = {"password": "Replacement123!"}
    assert api.client.put(url, json=payload, headers=api.headers).status_code == 403
    api.state["auth"] = {"id": api.admin, "role": "admin"}
    assert api.client.put(url, json=payload, headers=api.headers).status_code == 200
    assert db.verify_password("First", payload["password"])
    assert (
        api.client.put(
            f"/api/admin/users/{api.admin}/password", json=payload, headers=api.headers
        ).status_code
        == 400
    )


@pytest.mark.parametrize("role", ["guest", "teacher", "admin"])
def test_public_signup_is_unavailable_for_every_role(api, role):
    if role == "guest":
        api.state.pop("auth")
    else:
        api.state["auth"] = {"id": api.admin if role == "admin" else api.first, "role": role}
    before = len(db.list_users())
    response = api.client.post(
        "/api/signup",
        json={
            "username": "Self Registered",
            "email": "new@example.test",
            "password": "Secure-password1",
            "confirm_password": "Secure-password1",
        },
        headers=api.headers,
    )
    assert response.status_code == 404
    assert len(db.list_users()) == before


def test_account_creation_remains_admin_only(api):
    from backend.api.admin_routes import router

    api.client.app.include_router(router)
    payload = {
        "username": "New Teacher",
        "email": "new@example.test",
        "password": "Secure-password1",
    }
    assert api.client.post("/api/admin/users", json=payload, headers=api.headers).status_code == 403
    api.state.pop("auth")
    assert api.client.post("/api/admin/users", json=payload, headers=api.headers).status_code == 401
    api.state["auth"] = {"id": api.admin, "role": "admin"}
    response = api.client.post("/api/admin/users", json=payload, headers=api.headers)
    assert response.status_code == 201, response.text
    assert db.get_user_by_id(response.json()["id"])["role"] == "teacher"
