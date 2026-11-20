"""
backend/main.py
───────────
Application entry point.
Registers startup hooks and imports all pages (side-effect: @ui.page routes fire).
"""
import os
import logging
import sys
import threading

from nicegui import app as nicegui_app, ui

from backend.config import (
    BIND_HOST,
    BIND_PORT,
    INITIAL_ADMIN_PASSWORD,
    INITIAL_ADMIN_USERNAME,
    STORAGE_SECRET,
    get_ssl_kwargs,
)
from backend.db._core import _conn
from backend.db.database import (
    ensure_default_admin,
    finish_stale_runs,
    init_db,
    seed_classes,
)
from backend.services.monitor_service import drain_worker
from backend.services.retention_service import start_retention_worker
from backend.services.schedule_service import start_scheduler

log = logging.getLogger(__name__)

# Register the authenticated workstation channel.
from backend.core.agent_api import router as workstation_router
nicegui_app.include_router(workstation_router)

# Register pages
import frontend.pages.classroom_status
import frontend.pages.workstations
import frontend.pages.application_rules
import frontend.pages.admin_profile  # noqa: F401
import frontend.pages.teacher_profile  # noqa: F401
import frontend.pages.login      # noqa: F401
import frontend.pages.dashboard  # noqa: F401
import frontend.pages.history    # noqa: F401
import frontend.pages.analytics  # noqa: F401
import frontend.pages.alerts     # noqa: F401
import frontend.pages.reports    # noqa: F401
import frontend.pages.groups     # noqa: F401
import frontend.pages.schedules  # noqa: F401
import frontend.pages.models     # noqa: F401
import frontend.pages.audit      # noqa: F401
import frontend.pages.settings   # noqa: F401
import frontend.pages.users      # noqa: F401


def _bootstrap_admin() -> None:
    """
    On a fresh database (zero users), create the initial admin account
    using credentials supplied via the INITIAL_ADMIN_USERNAME /
    INITIAL_ADMIN_PASSWORD environment variables.

    Behaviour:
      • If a user already exists → no-op, returns immediately.
      • If DB is empty AND INITIAL_ADMIN_PASSWORD is unset → prints a clear
        instruction and exits with a non-zero status code.

    Note: in practice the exit path only triggers when an operator removed
    the password from an existing .env — backend/config.py auto-creates a
    missing .env with the documented admin/admin defaults, so a fresh
    install always boots with those credentials. Change the admin password
    through the UI after the first login.
    """
    c = _conn()
    from backend.db.staff_email import link_account_email, normalize_email
    admin_email = os.environ.get("INITIAL_ADMIN_EMAIL", "").strip()
    if c.execute("SELECT COUNT(*) FROM user").fetchone()[0]:
        if admin_email:
            legacy = c.execute(
                "SELECT u.id FROM user u JOIN role r ON r.id=u.role_id "
                "WHERE r.name='admin' AND u.username=? AND u.email IS NULL",
                (INITIAL_ADMIN_USERNAME,),
            ).fetchone()
            if legacy:
                link_account_email(legacy["id"], admin_email)
        return

    if not INITIAL_ADMIN_PASSWORD:
        sys.stderr.write(
            "\n"
            "ERROR: The database has no users yet and INITIAL_ADMIN_PASSWORD\n"
            "is not set. Add the following to your .env file:\n\n"
            "    INITIAL_ADMIN_USERNAME=admin\n"
            "    INITIAL_ADMIN_PASSWORD=<choose a strong password>\n\n"
            "Then restart. The variable is only consulted on a fresh database;\n"
            "once an account exists you can manage users through the UI.\n"
        )
        sys.exit(1)

    if not admin_email:
        raise RuntimeError("Set INITIAL_ADMIN_EMAIL in .env before starting a new database.")
    ensure_default_admin(INITIAL_ADMIN_USERNAME, INITIAL_ADMIN_PASSWORD, normalize_email(admin_email))
    log.info(
        "bootstrap: created initial admin %r from environment variable",
        INITIAL_ADMIN_USERNAME,
    )


@nicegui_app.on_startup
def _startup() -> None:
    init_db()
    seed_classes()
    _bootstrap_admin()
    # Close monitoring_run rows left 'running' by a crash/hard kill — must
    # happen before the scheduler can open a new run.
    n_stale = finish_stale_runs()
    if n_stale:
        log.info("startup: marked %d stale monitoring run(s) as interrupted", n_stale)
    threading.Thread(target=drain_worker, daemon=True, name="drain").start()
    start_scheduler()
    start_retention_worker()


# TLS (opt-in via TLS_ENABLED in .env). get_ssl_kwargs() raises on cert
# failure rather than falling back to plaintext — never start unencrypted
# when the operator asked for HTTPS. With TLS on, the session cookie also
# gets the Secure flag so it is never sent over an http:// connection.
_ssl = get_ssl_kwargs()
if _ssl:
    log.info("TLS enabled — serving HTTPS with certificate %s", _ssl["ssl_certfile"])

from backend.core.session_cookie import configure_login_cookie

configure_login_cookie(nicegui_app, STORAGE_SECRET, bool(_ssl))

ui.run(
    title          = "Velarora",
    # Explicit binding: 0.0.0.0 keeps the UI reachable from other machines on
    # the LAN (the normal deployment); override via BIND_HOST/BIND_PORT in .env.
    host           = BIND_HOST,
    port           = BIND_PORT,
    dark           = True,
    storage_secret = STORAGE_SECRET,
    favicon        = "🎓",
    show           = True,
    reload         = False,
    **_ssl,
)
