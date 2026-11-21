"""Serve the React application and redirect historical page bookmarks."""

from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse

DIST = Path(__file__).resolve().parents[2] / "frontend" / "react" / "dist"
router = APIRouter()


def register(app):
    from backend.api.admin_routes import router as api

    app.include_router(api)
    from backend.api import (
        auth_routes,
        teacher_routes,
        classroom_routes,
        management_routes,
        training_routes,
    )
    from backend.core.google_login import router as google_router

    for module in (
        auth_routes,
        teacher_routes,
        classroom_routes,
        management_routes,
        training_routes,
    ):
        app.include_router(module.router)
    app.include_router(google_router)
    app.add_static_files("/design-assets", str(DIST.parent.parent / "assets"))
    if (DIST / "assets").is_dir():
        app.add_static_files("/admin/assets", str(DIST / "assets"))
    app.include_router(router)
    from fastapi import Request
    from fastapi.responses import RedirectResponse

    routes = {
        "/": "welcome",
        "/welcome": "welcome",
        "/login": "login",
        "/signup": "signup",
        "/users": "users",
        "/groups": "classrooms",
        "/models": "models",
        "/audit": "audit",
        "/settings": "settings",
        "/profile": "profile",
        "/teacher-profile": "profile",
        "/history": "history",
        "/analytics": "analytics",
        "/reports": "reports",
        "/alerts": "app-rules",
        "/schedules": "schedules",
        "/workstations": "workstations",
        "/classroom-status": "classroom-overview",
        "/model-alert-rules": "model-alert-rules",
    }

    def old_page(destination):
        async def page(request: Request):
            query = ("?" + request.url.query) if request.url.query else ""
            return RedirectResponse(
                "/admin/" + destination + query,
                status_code=303,
                headers={"Cache-Control": "no-store"},
            )

        return page

    for path, destination in routes.items():
        app.add_api_route(path, old_page(destination), methods=["GET"], include_in_schema=False)

    @app.get("/auth/continue", include_in_schema=False)
    def continued(request: Request):
        from backend.core.auth import get_session_user
        from backend.api.admin_security import browser_state

        user = get_session_user()
        request.session["remember"] = bool(browser_state().get("remember_until"))
        destination = (
            "users" if user and user["role"] == "admin" else "dashboard" if user else "login"
        )
        return RedirectResponse(
            "/admin/" + destination, status_code=303, headers={"Cache-Control": "no-store"}
        )


@router.get("/admin/{path:path}", include_in_schema=False)
def react_admin(path: str = ""):
    if not (DIST / "index.html").is_file():
        return HTMLResponse(
            "React build missing. Run npm install and npm run build in frontend/react, then restart Velarora.",
            status_code=503,
        )
    return FileResponse(DIST / "index.html", headers={"Cache-Control": "no-store"})


def redirect_if_built(path):
    if not (DIST / "index.html").is_file():
        return False
    from nicegui import ui

    ui.navigate.to("/admin/" + path)
    return True
