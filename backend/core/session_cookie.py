"""Keep the signed login cookie for 30 days only when the user opts in."""
from starlette.middleware.sessions import SessionMiddleware

COOKIE = "velarora_session"
REMEMBER_SECONDS = 30 * 24 * 60 * 60


class BrowserCookieLifetime:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        async def send_cookie(message):
            if message["type"] == "http.response.start" and not scope.get("session", {}).get("remember"):
                headers = []
                for key, value in message["headers"]:
                    if key.lower() == b"set-cookie" and value.startswith(COOKIE.encode() + b"="):
                        value = b"; ".join(part for part in value.split(b"; ")
                                           if not part.lower().startswith(b"max-age="))
                    headers.append((key, value))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_cookie)


def configure_login_cookie(app, secret, https_only):
    app.add_middleware(SessionMiddleware, secret_key=secret, session_cookie=COOKIE,
                       max_age=REMEMBER_SECONDS, https_only=https_only)
    app.add_middleware(BrowserCookieLifetime)
