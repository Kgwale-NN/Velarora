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
    assert asyncio.run(google_login.finish_google(req)).headers["location"] == "/login?google=session"
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
    assert asyncio.run(google_login.finish_google(req)).headers["location"] == "/login?google=session"


def test_google_error_messages_do_not_include_secrets():
    from authlib.integrations.base_client.errors import OAuthError
    from httpx import ConnectError
    response = google_login.failure(OAuthError(error="invalid_client", description="private-secret"))
    assert response.headers["location"] == "/login?google=credentials"
    assert b"private-secret" not in response.body
    assert google_login.failure(ConnectError("private-url")).headers["location"] == "/login?google=network"

def test_google_issuer_variants_still_check_audience_and_nonce():
    import time
    import pytest
    from authlib.integrations.starlette_client import OAuth
    from joserfc import jwt
    from joserfc.jwk import RSAKey
    from joserfc.errors import InvalidClaimError
    key = RSAKey.generate_key(2048, parameters={"kid": "test-key"})
    client = OAuth().register("test", client_id="velarora-test")
    client.load_server_metadata = AsyncMock(return_value={"issuer": "https://accounts.google.com"})
    client.fetch_jwk_set = AsyncMock(return_value={"keys": [key.as_dict(private=False)]})
    options = {"iss": {"essential": True, "values": ["https://accounts.google.com", "accounts.google.com"]},
               "aud": {"essential": True, "value": "velarora-test"}}
    claims = {"iss": "https://accounts.google.com", "aud": "velarora-test", "sub": "test-user",
              "iat": int(time.time()), "exp": int(time.time()) + 300, "nonce": "expected-nonce"}

    def check(values):
        encoded = jwt.encode({"alg": "RS256", "kid": "test-key"}, values, key)
        return asyncio.run(client.parse_id_token({"id_token": encoded, "access_token": "test-access"},
                          nonce="expected-nonce", claims_options=options))

    for issuer in ("https://accounts.google.com", "accounts.google.com"):
        assert check(dict(claims, iss=issuer))["sub"] == "test-user"
    for changed in ({"iss": "https://untrusted.example"}, {"aud": "another-app"}, {"nonce": "wrong"}):
        with pytest.raises(InvalidClaimError):
            check(dict(claims, **changed))
