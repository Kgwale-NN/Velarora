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


def test_https_proxy_secures_cookies_without_changing_local_http():
    app = FastAPI()
    configure_login_cookie(app, "proxy-cookie-test", https_only=False)

    @app.get("/demo")
    def demo(request: Request):
        from fastapi.responses import JSONResponse
        request.session["remember"] = True
        response = JSONResponse({"ok": True})
        response.set_cookie("example", "not-a-secret", httponly=True)
        return response

    for base, secure in [("http://testserver", False), ("https://testserver", True)]:
        with TestClient(app, base_url=base) as browser:
            response = browser.get("/demo")
            headers = response.headers.get_list("set-cookie")
            assert len(headers) == 2
            for header in headers:
                attributes = {part.strip().lower() for part in header.split(";")[1:]}
                assert ("secure" in attributes) is secure
                assert "httponly" in attributes
