from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.core.session_cookie import COOKIE, REMEMBER_SECONDS, configure_login_cookie


def test_browser_close_and_sign_out():
    app = FastAPI()
    configure_login_cookie(app, "test-only-secret", https_only=True)

    @app.get("/choice/{remember}")
    def choice(request: Request, remember: bool):
        request.session["remember"] = remember
        return {"remember": remember}

    @app.get("/current")
    def current(request: Request):
        return request.session.get("remember")

    with TestClient(app, base_url="https://testserver") as browser:
        header = browser.get("/choice/false").headers["set-cookie"].lower()
        assert "max-age" not in header and "httponly" in header and "secure" in header
        browser.cookies.jar.clear_session_cookies()
        assert browser.get("/current").json() is None
        header = browser.get("/choice/true").headers["set-cookie"].lower()
        assert f"max-age={REMEMBER_SECONDS}" in header
        browser.cookies.jar.clear_session_cookies()
        assert browser.get("/current").json() is True
        browser.get("/choice/false")
        browser.cookies.jar.clear_session_cookies()
        assert COOKIE not in browser.cookies
