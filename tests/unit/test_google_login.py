import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from starlette.requests import Request
from backend.core import google_login


def test_google_callback_checks_state_and_consumes_attempt(monkeypatch):
    store = {}
    monkeypatch.setattr(google_login, "app", SimpleNamespace(storage=SimpleNamespace(user=store)))
    google = AsyncMock()
    monkeypatch.setattr(google_login, "google", google)
    req = Request({"type": "http", "query_string": b"state=wrong"})
    asyncio.run(google_login.start_google(req, True))
    assert asyncio.run(google_login.finish_google(req)).headers["location"] == "/login?google=failed"
    google.authorize_access_token.assert_not_awaited()
    asyncio.run(google_login.start_google(req, True))
    state = store["google_attempt"]["state"]
    req = Request({"type": "http", "query_string": ("state=" + state).encode()})
    google.authorize_access_token.return_value = {"id_token": "test", "userinfo": {"sub": "1"}}
    user = {"id": 2, "role": "teacher", "username": "Sam"}
    monkeypatch.setattr(google_login, "google_account", lambda claims: user)
    login = Mock()
    monkeypatch.setattr(google_login, "set_session_user", login)
    assert asyncio.run(google_login.finish_google(req)).headers["location"] == "/auth/continue"
    login.assert_called_once_with(user, remember=True)
    assert asyncio.run(google_login.finish_google(req)).headers["location"] == "/login?google=failed"
