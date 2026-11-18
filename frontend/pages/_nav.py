"""
frontend/pages/_nav.py
─────────────────
Shared navigation bar — role-aware.

Roles
─────
  admin   — Users, Models, Audit Log, Admin Profile, Settings
  teacher — Dashboard, History, Analytics, Reports, Alert Rules, Groups,
            Schedules, My Profile
            + Start/Stop monitor + notification bell
  student — My History, My Analytics
"""
from __future__ import annotations

from nicegui import app as nicegui_app, run, ui

from backend.core.auth import clear_session
from frontend.pages._snapshot import make_snapshot_dialogs
from frontend.pages.glass_fields import text_field
from frontend.translate import t, get_lang, set_lang


def nav(current_user: dict) -> None:
    role = current_user["role"]

    if role in ("admin", "teacher"):
        from frontend.pages.admin_shell import workspace_nav
        workspace_nav(current_user)
        return

    dark = ui.dark_mode()
    dark.enable() if nicegui_app.storage.user.get("dark_mode", True) else dark.disable()
    with ui.header().classes("bg-gray-900 text-white px-4 py-2 flex items-center gap-4 shadow-md"):
        ui.label("🎓 Velarora").classes("font-bold text-base mr-2")
        for key, path in [("nav_my_history", "/history"), ("nav_my_analytics", "/analytics")]:
            ui.link(t(key), path).classes("text-gray-300 hover:text-white text-sm no-underline")
        with ui.row().classes("ml-auto items-center"):
            _user_menu(current_user, dark)


# ── User menu ─────────────────────────────────────────────────────────────────

def _user_menu(current_user: dict, dark, on_logout=None):
    role = current_user["role"]

    pwd_dlg = password_dialog(current_user)

    role_label = t(f"users_role_{role}")
    label_text = f"{current_user['username']}  ({role_label})"
    with ui.dropdown_button(
        label_text, icon="account_circle",
    ).props("flat no-caps dense color=white") as account_menu:

        with ui.menu_item():
            with ui.row().classes("items-center gap-3 w-full"):
                ui.icon("dark_mode").classes("text-base")
                ui.label(t("nav_dark_mode")).classes("text-sm flex-1")
                ui.switch(
                    value=nicegui_app.storage.user.get("dark_mode", True),
                    on_change=lambda e: (
                        nicegui_app.storage.user.__setitem__("dark_mode", e.value),
                        dark.enable() if e.value else dark.disable(),
                    ),
                ).props("dense")

        ui.separator()

        # ── Language switcher ──────────────────────────────────────────────────
        with ui.menu_item():
            with ui.row().classes("items-center gap-3 w-full"):
                ui.icon("translate").classes("text-base")
                ui.label("EN / LT").classes("text-sm flex-1")
                lang_now = get_lang()
                ui.toggle(
                    {"en": "EN", "lt": "LT"},
                    value=lang_now,
                    on_change=lambda e: (set_lang(e.value), ui.navigate.reload()),
                ).props("dense")

        ui.separator()

        if role == 'teacher':
            with ui.menu_item(on_click=lambda: ui.navigate.to('/teacher-profile')):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('person_outline').classes('text-base')
                    ui.label('My Profile').classes('text-sm')
            ui.separator()

        with ui.menu_item(on_click=pwd_dlg.open):
            with ui.row().classes("items-center gap-3"):
                ui.icon("lock").classes("text-base")
                ui.label(t("nav_change_password")).classes("text-sm")

        ui.separator()

        with ui.menu_item(
            on_click=on_logout or (lambda: (clear_session(), ui.navigate.to("/auth/continue")))
        ):
            with ui.row().classes("items-center gap-3 text-red-400"):
                ui.icon("logout").classes("text-base")
                ui.label(t("nav_sign_out")).classes("text-sm")

    account_menu.bind_text_from(nicegui_app.storage.user, 'auth', backward=lambda account:
        f"{(account or current_user)['username']}  ({role_label})")
    return account_menu


def password_dialog(current_user: dict):
    from frontend.pages.design_assets import stylesheet
    stylesheet('teacher-profile.css')
    with ui.dialog() as pwd_dlg, ui.card().classes('account-password-dialog'):
        with ui.row().classes('account-dialog-heading w-full items-start justify-between'):
            ui.label(t('pwd_title')).classes('account-dialog-title')
            ui.button(icon='close',on_click=pwd_dlg.close).props('flat round aria-label="Close password dialog"')
        current_pw = text_field(t("pwd_current"), icon="lock_outline", password=True,
                                props="autocomplete=current-password", placeholder="Enter your current password")
        new_pw = text_field(t("pwd_new"), icon="lock_outline", new_password=True, placeholder="Create a strong password")
        confirm_pw = text_field(t("pwd_confirm"), icon="lock_outline", password=True,
                                props="autocomplete=new-password", placeholder="Re-enter your new password")
        err_lbl = ui.label("").classes("account-form-error").props("role=alert")

        async def do_change() -> None:
            from backend.db.database import validate_password, update_password
            from backend.db.user_queries import verify_password_by_id
            if save_password._props.get("loading"):
                return
            old_value, new_value, confirmation = current_pw.value, new_pw.value, confirm_pw.value
            save_password.props("loading")
            try:
                if not await run.io_bound(verify_password_by_id, current_user["id"], old_value):
                    err_lbl.set_text(t("pwd_err_wrong"))
                    return
                try:
                    validate_password(new_value)
                except ValueError as exc:
                    err_lbl.set_text(str(exc))
                    return
                if new_value != confirmation:
                    err_lbl.set_text(t("pwd_err_mismatch"))
                    return
                await run.io_bound(update_password, current_user["id"], new_value)
                pwd_dlg.close()
                current_pw.set_value("")
                new_pw.set_value("")
                confirm_pw.set_value("")
                err_lbl.set_text("")
                from frontend.pages.admin_shell import toast
                toast(t("pwd_success"), type="positive")
            except Exception:
                import logging
                logging.getLogger(__name__).exception('Password change failed')
                err_lbl.set_text('The password could not be changed. Please try again.')
            finally:
                save_password.props(remove="loading")

        with ui.row().classes('account-dialog-footer w-full justify-end gap-3'):
            ui.button(t('pwd_cancel'),on_click=pwd_dlg.close).props('flat no-caps')
            save_password = ui.button(t('pwd_save'),icon='check',on_click=do_change).props('no-caps')

    return pwd_dlg


# ── Notification bell ─────────────────────────────────────────────────────────

def _notification_bell() -> None:
    from frontend.pages.admin_shell import toast
    from backend.db.database import (
        count_unread_notifications,
        get_event_frame_b64,
        get_event_frame_annotated_b64,
        list_notifications,
        mark_all_read,
        mark_read,
    )

    _snap_dlg, _fs_dlg, show_snapshot = make_snapshot_dialogs()

    # ── Notification list dialog ──────────────────────────────────────────────
    with ui.dialog().props("position=right") as notif_dlg, \
         ui.card().classes("p-0 h-full rounded-none").style(
             "width:400px; max-width:95vw;"):
        with ui.row().classes("items-center justify-between px-4 py-3 w-full"):
            ui.label(t("notif_title")).classes("text-base font-bold")
            ui.button(
                t("notif_mark_all_read"),
                on_click=lambda: (mark_all_read(), _reload(), _refresh_badge()),
            ).props("flat dense size=sm color=gray")
        ui.separator()
        scroll = ui.scroll_area().classes("w-full").style(
            "flex:1; height:calc(100vh - 64px);")

    def _reload() -> None:
        scroll.clear()
        with scroll:
            items = list_notifications(limit=60)
            if not items:
                with ui.column().classes("items-center w-full p-10 gap-3"):
                    ui.icon("notifications_none").classes("text-5xl text-gray-600")
                    ui.label(t("notif_empty")).classes(
                        "text-gray-500 text-sm")
                return
            for n in items:
                _render_row(n)

    def _render_row(n: dict) -> None:
        color  = n.get("class_color", "#888")
        is_new = not bool(n["is_read"])
        bg     = "bg-blue-50 dark:bg-gray-800" if is_new else ""

        with ui.card().classes(
            f"w-full rounded-none border-0 shadow-none {bg}"
        ).style(
            f"border-left:4px solid {color}; border-radius:0 !important;"
        ):
            with ui.row().classes("items-start gap-2 px-3 py-2 w-full"):
                with ui.column().classes("gap-1 flex-1 min-w-0"):
                    with ui.row().classes("items-center gap-2 flex-wrap"):
                        ui.badge(n["class_name"]).props("rounded").style(
                            f"background:{color}; color:#fff; font-size:0.68rem;")
                        if is_new:
                            ui.badge("NEW").props("rounded color=orange")
                    ui.label(f"🖥  {n['computer']}").classes("text-xs text-gray-700 dark:text-gray-300")
                    ui.label(f"👤 {n['student']}").classes("text-xs text-gray-700 dark:text-gray-300")
                    ui.label(n["created_at"]).classes("text-xs text-gray-500 dark:text-gray-400")

                if n.get("has_frame"):
                    meta_str = (
                        f"{n['class_name']}  •  {n['computer']}"
                        f"  •  {n['student']}  •  {n['created_at']}"
                    )

                    def _view(nid=n["id"], eid=n["event_id"], meta=meta_str) -> None:
                        mark_read(nid)
                        _refresh_badge()
                        _reload()
                        raw_b64 = get_event_frame_b64(eid)
                        if raw_b64:
                            ann_b64 = get_event_frame_annotated_b64(eid)
                            show_snapshot(raw_b64, meta, ann_b64)
                        else:
                            toast(t("notif_no_snapshot"), type="warning")

                    ui.button(icon="image", on_click=_view).props(
                        "flat round dense color=blue"
                    ).tooltip(t("notif_view_snapshot"))

    def _open_notifs() -> None:
        _reload()
        notif_dlg.open()

    with ui.button(icon="notifications", on_click=_open_notifs).props(
        'flat round color=white aria-label="Notifications"'
    ):
        badge = ui.badge("").props("floating color=red transparent")

    _prev = [0]
    _computer_last_notif: dict[str, float] = {}
    _NOTIF_COOLDOWN = 5.0  # seconds between on-screen popups per computer

    def _refresh_badge() -> None:
        import time
        c = count_unread_notifications()
        badge.set_text(str(c) if c else "")
        badge.set_visibility(c > 0)

        if c > _prev[0]:
            new_items = list_notifications(limit=c - _prev[0])
            now = time.monotonic()
            shown = 0
            for n in new_items:
                computer = n['computer']
                if now - _computer_last_notif.get(computer, 0) < _NOTIF_COOLDOWN:
                    continue
                _computer_last_notif[computer] = now
                toast(
                    f"🚨 {n['class_name']} detected\n"
                    f"🖥  {computer}   👤 {n['student']}\n"
                    f"🕐 {n['created_at']}",
                    type="negative",
                    position="top-right",
                    timeout=8000,
                    close_button=True,
                )
                shown += 1
                if shown >= 3:
                    break
            if not shown:
                _prev[0] = c
                return
            ui.run_javascript("""
                (function(){
                  try {
                    const c=new(window.AudioContext||window.webkitAudioContext)();
                    function b(f,s,d,v){
                      const o=c.createOscillator(),g=c.createGain();
                      o.connect(g);g.connect(c.destination);
                      o.type='sine';o.frequency.value=f;
                      g.gain.setValueAtTime(v,c.currentTime+s);
                      g.gain.exponentialRampToValueAtTime(
                        0.001,c.currentTime+s+d);
                      o.start(c.currentTime+s);
                      o.stop(c.currentTime+s+d+0.05);
                    }
                    b(880,0.0,0.18,0.4);b(660,0.2,0.18,0.4);
                    b(880,0.4,0.25,0.5);
                  } catch(e){}
                })();
            """)

        _prev[0] = c

    _refresh_badge()
    ui.timer(3.0, _refresh_badge)
