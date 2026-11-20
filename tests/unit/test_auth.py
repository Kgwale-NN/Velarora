"""
tests/unit/test_auth.py
──────────────────
Tests for backend/core/auth.py session helpers.
NiceGUI's app.storage.user and ui.navigate.to are mocked so these tests
run without a running NiceGUI server.

Run:  pytest tests/unit/test_auth.py -v
"""
from __future__ import annotations
from unittest.mock import MagicMock, patch


# ── Fixture: patch NiceGUI at import time ─────────────────────────────────────

def _make_storage(initial: dict | None = None):
    """Return a plain dict that behaves like app.storage.user."""
    return initial or {}


def _import_auth(storage: dict):
    """Re-import auth with a fresh NiceGUI mock each time."""
    import sys
    mock_app = MagicMock()
    mock_app.storage.user = storage
    mock_ui  = MagicMock()
    with patch.dict(sys.modules, {
        "nicegui":    MagicMock(app=mock_app, ui=mock_ui),
    }):
        if "backend.core.auth" in sys.modules:
            del sys.modules["backend.core.auth"]
        import backend.core.auth as auth
        auth.nicegui_app = mock_app
        auth.ui          = mock_ui
    return auth, mock_app, mock_ui


# ── get_session_user ──────────────────────────────────────────────────────────

class TestGetSessionUser:
    def test_returns_none_when_empty(self):
        auth, app_, _ = _import_auth({})
        assert auth.get_session_user() is None

    def test_returns_stored_user(self):
        user = {"id": 1, "username": "admin", "role": "teacher"}
        auth, app_, _ = _import_auth({"auth": user})
        assert auth.get_session_user() == user


# ── set_session_user ──────────────────────────────────────────────────────────

class TestSetSessionUser:
    def test_stores_correct_fields(self):
        storage = {}
        auth, _, _ = _import_auth(storage)
        auth.set_session_user({"id": 5, "username": "jonas", "role": "teacher",
                               "extra": "should_be_dropped"})
        assert storage["auth"] == {"id": 5, "username": "jonas", "role": "teacher"}

    def test_overwrites_existing(self):
        storage = {"auth": {"id": 1, "username": "old", "role": "teacher"}}
        auth, _, _ = _import_auth(storage)
        auth.set_session_user({"id": 2, "username": "new", "role": "admin"})
        assert storage["auth"]["username"] == "new"


# ── clear_session ─────────────────────────────────────────────────────────────

class TestClearSession:
    def test_removes_auth_key(self):
        storage = {"auth": {"id": 1, "username": "x", "role": "teacher"}}
        auth, _, _ = _import_auth(storage)
        auth.clear_session()
        assert "auth" not in storage

    def test_safe_when_already_empty(self):
        auth, _, _ = _import_auth({})
        auth.clear_session()   # should not raise


# ── require_auth ──────────────────────────────────────────────────────────────

class TestRequireAuth:
    def test_redirects_to_login_when_no_session(self):
        auth, _, mock_ui = _import_auth({})
        result = auth.require_auth()
        mock_ui.navigate.to.assert_called_once_with("/login")
        assert result is None

    def test_returns_user_when_authenticated(self):
        user = {"id": 1, "username": "admin", "role": "teacher"}
        auth, _, _ = _import_auth({"auth": user})
        assert auth.require_auth() == user

    def test_redirects_when_wrong_role(self):
        # Wrong-role users get sent to their own home page (not a fixed "/"),
        # otherwise students/admins hit an infinite reload loop on teacher-only "/".
        user = {"id": 2, "username": "jonas", "role": "student"}
        auth, _, mock_ui = _import_auth({"auth": user})
        result = auth.require_auth(required_role="teacher")
        mock_ui.navigate.to.assert_called_once_with("/login")
        assert result is None

    def test_passes_when_correct_role(self):
        user = {"id": 1, "username": "admin", "role": "teacher"}
        auth, _, _ = _import_auth({"auth": user})
        assert auth.require_auth(required_role="teacher") == user

    def test_no_role_required_accepts_any_role(self):
        for role in ("teacher", "admin"):
            user = {"id": 1, "username": "x", "role": role}
            auth, _, _ = _import_auth({"auth": user})
            assert auth.require_auth() is not None
def test_remembered_login_expires_and_logout_revokes_it():
    from time import time
    storage = {}
    auth, _, _ = _import_auth(storage)
    user = {"id": 1, "username": "Teacher", "role": "teacher"}
    auth.set_session_user(user, remember=True)
    assert storage["remember_until"] > time()
    storage["remember_until"] = time() - 1
    assert auth.get_session_user() is None
    auth.set_session_user(user, remember=True)
    auth.clear_session()
    assert auth.get_session_user() is None and "remember_until" not in storage


def test_admin_only_access_rejects_teacher_and_student():
    for role, home in [('teacher', '/'), ('student', '/login')]:
        user = {'id': 1, 'username': 'Preview', 'role': role}
        auth, _, mock_ui = _import_auth({'auth': user})
        assert auth.require_auth(required_role='admin') is None
        mock_ui.navigate.to.assert_called_once_with(home)


def test_admin_only_access_accepts_admin():
    user = {'id': 1, 'username': 'Admin', 'role': 'admin'}
    auth, _, mock_ui = _import_auth({'auth': user})
    assert auth.require_auth(required_role='admin') == user
    mock_ui.navigate.to.assert_not_called()


def test_existing_student_session_is_revoked_for_every_page():
    storage = {'auth': {'id': 1, 'username': 'Learner', 'role': 'student'},
               'remember_until': 9999999999}
    auth, _, navigate = _import_auth(storage)
    assert auth.require_auth() is None
    assert 'auth' not in storage and 'remember_until' not in storage
    navigate.navigate.to.assert_called_once_with('/login')


def test_student_cannot_receive_a_new_or_remembered_session():
    import pytest
    storage = {'auth': {'id': 2, 'username': 'Old', 'role': 'teacher'}}
    auth, _, _ = _import_auth(storage)
    with pytest.raises(ValueError, match='Only staff'):
        auth.set_session_user({'id': 1, 'username': 'Learner', 'role': 'student'}, remember=True)
    assert 'auth' not in storage and 'remember_until' not in storage
