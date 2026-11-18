"""
frontend/pages/dashboard.py
──────────────────────
Dashboard page  /   (teacher only)
Live annotated preview + console log + Start/Stop.
Annotation overlay can be toggled on/off via the switch in the preview card.
"""
from nicegui import ui

import backend.state as state
from backend.config import collect_cfg
from backend.core.auth import require_auth
from backend.core.yolo import reset_model
from backend.db.database import get_active_model, list_groups, list_computers_in_group, log_action
from frontend.pages._nav import nav
from frontend.pages.admin_shell import toast
from frontend.pages.design_assets import stylesheet
from frontend.pages.glass_fields import select_field
from backend.services.monitor_service import MonitorController
from frontend.translate import t


@ui.page("/")
def page_dashboard() -> None:
    current = require_auth(required_role="teacher")
    if current is None:
        return
    nav(current)

    stylesheet("teacher-dashboard.css")
    with ui.column().classes("teacher-dashboard w-full"):
        with ui.column().classes("dashboard-heading"):
            ui.label("Your classroom, at a glance.").classes("dashboard-title")
            ui.label("Choose a group, start monitoring, and view a computer below.").classes("dashboard-subtitle")

        with ui.card().classes("dashboard-controls w-full"):
            with ui.row().classes("dashboard-section-heading w-full items-center justify-between"):
                with ui.row().classes("items-center gap-3"):
                    ui.icon("desktop_windows").classes("dashboard-section-icon")
                    ui.label("Monitoring").classes("dashboard-section-title")
                running = state.monitor is not None
                def _status_text():
                    if state.monitor is None:
                        return t("status_stopped")
                    group = state.monitored_group_name
                    return t("status_running_group").format(g=group) if group else t("status_running_all")
                status_lbl = ui.label(_status_text()).classes(
                    "dashboard-status " + ("is-running" if running else "is-stopped"))
            with ui.element("div").classes("dashboard-controls-grid w-full"):
                groups = list_groups()
                group_opts = {0: t("dash_all_computers")}
                group_opts.update({g["id"]: g["name"] for g in groups})
                group_sel = select_field("Group", group_opts, value=0, icon="groups")
                group_sel.tooltip(t("dash_group_tooltip"))
                pc_sel = select_field("Computer", list(state.latest_frames),
                                      value=next(iter(state.latest_frames), None), icon="computer")
                with ui.row().classes("dashboard-control-actions"):
                    btn_start = ui.button("Start", icon="play_arrow").props('no-caps aria-label="Start monitoring"')
                    btn_stop = ui.button("Stop", icon="stop").props("no-caps outline")
                if running:
                    btn_start.props("disable")
                    group_sel.props("disable")
                else:
                    btn_stop.props("disable")

        with ui.element("div").classes("dashboard-workspace w-full"):
            with ui.column().classes("dashboard-preview-column"):
                with ui.card().classes("dashboard-preview-card w-full"):
                    with ui.row().classes("dashboard-section-heading w-full items-center justify-between"):
                        with ui.row().classes("items-center gap-3"):
                            ui.icon("visibility").classes("dashboard-section-icon")
                            ui.label(t("dash_live_preview")).classes("dashboard-section-title")
                        ann_switch = ui.switch(t("dash_annotations"), value=True).props("dense")
                        ann_switch.tooltip(t("dash_ann_tooltip"))
                    offline_badge = ui.label(t("dash_offline_badge")).classes("dashboard-offline")
                    offline_badge.set_visibility(False)
                    with ui.element("div").classes("dashboard-preview-stage"):
                        with ui.column().classes("dashboard-preview-empty items-center justify-center") as empty_preview:
                            ui.icon("desktop_windows").classes("dashboard-empty-icon")
                            empty_title = ui.label("Ready when you are").classes("dashboard-empty-title")
                            empty_hint = ui.label("Start monitoring to see a computer screen here.").classes("dashboard-empty-hint")
                        live_img = ui.image("").props('no-spinner fit=contain alt="Selected computer screen"').classes("dashboard-live-image w-full")
                        live_img.set_visibility(False)
                with ui.element("div").classes("dashboard-details w-full"):
                    with ui.card().classes("dashboard-detail-card"):
                        ui.icon("person_outline").classes("dashboard-section-icon")
                        ui.label(t("dash_active_student")).classes("dashboard-detail-label")
                        student_lbl = ui.label("—").classes("dashboard-detail-value")
                    with ui.card().classes("dashboard-detail-card"):
                        ui.icon("find_in_page").classes("dashboard-section-icon")
                        ui.label(t("dash_last_detections")).classes("dashboard-detail-label")
                        det_info = ui.label(t("dash_no_detections")).classes("dashboard-detail-value")
            with ui.card().classes("dashboard-console"):
                with ui.row().classes("dashboard-section-heading w-full items-center justify-between"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("terminal").classes("dashboard-section-icon")
                        ui.label("Activity log").classes("dashboard-section-title")
                    ui.button("Clear", icon="delete_sweep", on_click=lambda: (
                        log_view.set_value(""), log_seq.__setitem__(0, state.log_total),
                    )).props('flat no-caps aria-label="Clear activity log"')
                ui.label("Newest activity appears first.").classes("dashboard-console-hint")
                log_view = ui.textarea(value="").props(
                    'readonly outlined rows=14 aria-label="Monitoring activity log"'
                ).classes("dashboard-log w-full")

    log_seq = [0]          # how many total log messages we have already displayed
    _last_src:    list[str]       = [""]   # deduplicate set_source calls → no flicker
    _mon_names:   list[set[str]]  = [set()]  # computer names for the active session

    # ── Button handlers ───────────────────────────────────────────────────────

    def do_start() -> None:
        # Check-then-assign on state.monitor must be atomic across the UI
        # thread and the scheduler thread; otherwise both could create their
        # own MonitorController and leak one of them.
        with state.monitor_lock:
            if state.monitor:
                return
            if not get_active_model():
                toast(t("dash_no_active_model"), type="warning")
                return
            try:
                cfg = collect_cfg()
            except (ValueError, KeyError) as e:
                toast(t("dash_cfg_error").format(e=e), type="negative"); return

            # Resolve computers for the selected group (0 = all)
            gid   = group_sel.value   # 0 = all computers, >0 = group id
            gname = group_opts.get(gid, "") if gid else ""

            computers: list[dict] | None = None
            if gid:
                rows = list_computers_in_group(gid)
                if not rows:
                    toast(
                        t("dash_no_computers").format(gname=gname), type="warning"
                    )
                    return
                computers = [{"name": r["name"], "host": r["host_address"]} for r in rows]

            reset_model()
            state.monitor = MonitorController(
                cfg, computers=computers,
                started_by=current["id"],
                group_name=gname if gid else "",
            )
            state.monitor.start()
            state.monitored_group_name = gname if gid else ""
            _mon_names[0] = {c["name"] for c in computers} if computers else set()
            log_action("monitor.start", user_id=current["id"],
                       detail=f"group={gname or 'all'}")
            btn_start.props("disable")
            btn_stop.props(remove="disable")
            group_sel.props("disable")
            label = (
                t("status_running_group").format(g=gname)
                if gid else t("status_running_all")
            )
            status_lbl.set_text(label)
            status_lbl.classes(
                replace="dashboard-status is-running")

    def do_stop() -> None:
        with state.monitor_lock:
            if state.monitor:
                state.monitor.stop()
                state.monitor = None
            state.consecutive_detections.clear()
            state.schedule_triggered    = False   # manual stop overrides scheduler
            state.monitored_group_name  = None
            _mon_names[0] = set()
            log_action("monitor.stop", user_id=current["id"], detail="manual")
            btn_start.props(remove="disable")
            btn_stop.props("disable")
            group_sel.props(remove="disable")
            status_lbl.set_text(t("status_stopped"))
        status_lbl.classes(
            replace="dashboard-status is-stopped")

    btn_start.on_click(do_start)
    btn_stop.on_click(do_stop)

    # ── 100 ms UI refresh ─────────────────────────────────────────────────────

    def tick() -> None:
        # ── Console: prepend new lines so newest appears at the top ───────────
        # Use a monotonic total counter so we never lose entries when the buffer
        # trims old messages from the front (pop(0) shifts all list indices).
        total = state.log_total
        new_count = total - log_seq[0]
        if new_count > 0:
            log_seq[0] = total
            # The buffer holds at most LOG_CAP entries (most recent).
            # Grab the last new_count entries — clamped to what's available.
            buf = state.log_buffer
            new = buf[max(0, len(buf) - new_count):]
            new_block = "\n".join(reversed(new))
            old = log_view.value or ""
            combined = new_block + ("\n" + old if old else "")
            # Cap at 400 lines to prevent unbounded growth
            lines = combined.split("\n")
            if len(lines) > 400:
                combined = "\n".join(lines[:400])
            log_view.set_value(combined)

        # ── Keep status / buttons in sync with scheduler-driven start/stop ────
        if state.monitor is not None:
            g = state.monitored_group_name
            lbl = (
                t("status_running_group").format(g=g)
                if g else t("status_running_all")
            )
            if status_lbl.text != lbl:
                status_lbl.set_text(lbl)
                status_lbl.classes(
                    replace="dashboard-status is-running")
                btn_start.props("disable")
                btn_stop.props(remove="disable")
                group_sel.props("disable")
        else:
            stopped = t("status_stopped")
            if status_lbl.text != stopped:
                status_lbl.set_text(stopped)
                status_lbl.classes(
                    replace="dashboard-status is-stopped")
                btn_start.props(remove="disable")
                btn_stop.props("disable")
                group_sel.props(remove="disable")
                _mon_names[0] = set()

        # ── Computer selector: only show computers in the monitored group ─────
        all_opts = list(state.latest_frames.keys())
        filter_names = _mon_names[0]
        opts = [n for n in all_opts if n in filter_names] if filter_names else all_opts

        # Build a {value: label} mapping so offline machines visibly carry the
        # "(offline)" suffix without changing the option value (which is the
        # raw computer name). NiceGUI's ui.select supports both list and dict
        # forms for `options`.
        offline_suffix = t("dash_offline_suffix")
        opts_map = {
            n: (f"{n}  {offline_suffix}" if not state.is_computer_online(n) else n)
            for n in opts
        }
        if opts_map != (pc_sel.options or {}):
            pc_sel.options = opts_map
            pc_sel.update()
            if pc_sel.value not in opts_map:
                pc_sel.set_value(next(iter(opts_map), None))

        sel = pc_sel.value
        if sel and sel in state.latest_frames:
            ann_b64, raw_b64, dets = state.latest_frames[sel]

            has_frame = bool(ann_b64 if ann_switch.value else raw_b64)
            live_img.set_visibility(has_frame)
            empty_preview.set_visibility(not has_frame)
            # Only push to the DOM when the frame actually changed — eliminates flicker
            src = ann_b64 if ann_switch.value else raw_b64
            if src != _last_src[0]:
                _last_src[0] = src
                live_img.set_source(src)

            # Toggle the OFFLINE badge for the currently selected computer.
            offline_badge.set_visibility(not state.is_computer_online(sel))

            uid = state.computer_users.get(sel)
            if uid:
                from backend.db.database import get_user_by_id
                u = get_user_by_id(uid)
                student_lbl.set_text(u["username"] if u else "—")
            else:
                student_lbl.set_text(t("dash_not_matched"))

            det_info.set_text(
                "  |  ".join(
                    f"{d['class_name']} {d['conf']:.0%}" for d in dets)
                if dets else t("dash_no_detections")
            )
        else:
            # Clear stale data when a selection disappears; never leave another PC's screen visible.
            offline_badge.set_visibility(False)
            live_img.set_visibility(False)
            empty_preview.set_visibility(True)
            if _last_src[0]:
                _last_src[0] = ""
                live_img.set_source("")
            student_lbl.set_text("—")
            det_info.set_text(t("dash_no_detections"))
        if state.monitor is not None:
            empty_title.set_text("Waiting for a screen")
            empty_hint.set_text("Choose a computer once its first screen arrives.")
        else:
            empty_title.set_text("Ready when you are")
            empty_hint.set_text("Start monitoring to see a computer screen here.")

    ui.timer(0.1, tick)
