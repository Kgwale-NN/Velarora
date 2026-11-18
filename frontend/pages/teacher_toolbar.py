"""Teacher monitoring and training controls, shared across teacher pages."""
from nicegui import ui
import backend.state as state
from frontend.translate import t
from frontend.pages.admin_shell import toast


def monitoring_controls(current_user):
    status_dot = ui.label("").classes("teacher-monitor-status text-xs")
    btn_start  = ui.button(t("btn_start").lstrip("▶ "), icon="play_arrow").props(
        'no-caps aria-label="Start monitoring"').classes("teacher-header-start")
    btn_stop   = ui.button(t("btn_stop").lstrip("■ "), icon="stop").props(
        'no-caps aria-label="Stop monitoring"').classes("teacher-header-stop")

    def do_start() -> None:
        if state.monitor:
            return
        from backend.db.database import get_active_model
        if not get_active_model():
            toast(t("dash_no_active_model"), type="warning")
            return
        from backend.config import collect_cfg
        from backend.core.yolo import reset_model
        from backend.services.monitor_service import MonitorController
        try:
            cfg = collect_cfg()
        except (ValueError, KeyError) as e:
            toast(t("dash_cfg_error").format(e=e), type="negative")
            return
        reset_model()
        state.monitor = MonitorController(
            cfg, started_by=current_user["id"], group_name="")
        state.monitor.start()

    def do_stop() -> None:
        if state.monitor:
            state.monitor.stop()
            state.monitor = None
        state.schedule_triggered   = False   # manual stop overrides scheduler
        state.monitored_group_name = None

    btn_start.on_click(do_start)
    btn_stop.on_click(do_stop)

    def _sync_buttons() -> None:
        running = state.monitor is not None
        if running:
            g = state.monitored_group_name
            if g:
                label = t("status_running_group").format(g=g)
            else:
                label = t("status_running_all")
            status_dot.set_text(label)
            status_dot.classes(replace="teacher-monitor-status text-xs text-green-400")
            btn_start.props("disable")
            btn_stop.props(remove="disable")
        else:
            status_dot.set_text(t("status_stopped"))
            status_dot.classes(replace="teacher-monitor-status text-xs text-red-400")
            btn_start.props(remove="disable")
            btn_stop.props("disable")

    _sync_buttons()
    ui.timer(1.0, _sync_buttons)


def training_progress():
    with ui.row().classes("items-center gap-1") as train_chip_row:
        ui.icon("psychology", size="xs").classes(
            "text-gray-300")
        train_chip_lbl = ui.label("").classes(
            "teacher-monitor-status text-xs text-gray-300")
        ui.link(t("nav_models"), "/models").classes(
            "text-xs text-gray-300 no-underline hover:text-white")
    train_chip_row.set_visibility(False)

    def _sync_training() -> None:
        w = state.training_worker
        if w and w.is_running:
            train_chip_row.set_visibility(True)
            bp = w.batch_progress
            ep    = bp.get("epoch", 0)
            total = bp.get("total_epochs", 0)
            if total:
                train_chip_lbl.set_text(f"ep {ep}/{total}")
            else:
                raw = w.current_status or t("nav_training_running")
                train_chip_lbl.set_text(raw[:30])
        else:
            train_chip_row.set_visibility(False)

    _sync_training()
    ui.timer(2.0, _sync_training)
