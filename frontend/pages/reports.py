"""
frontend/pages/reports.py
────────────────────
Reports page  /reports  (teacher only)

One row per monitoring run (manual or scheduler-triggered). Selecting a run
opens its detection report: summary cards, an alerts section (prohibited
classes, grouped per class, with per-alert screenshot viewing), and
collapsible per-class / per-student / per-computer breakdowns. The report
can be exported as CSV (every individual detection) or PDF (the full
report, print-ready). Reports are computed live from the run's
detection_event rows, so they are always consistent with the History page.
"""
from __future__ import annotations

import logging

from nicegui import run, ui

from backend.core.auth import require_auth
from backend.db.database import (
    get_event_frame_annotated_b64 as _source_get_event_frame_annotated_b64,
    get_event_frame_b64 as _source_get_event_frame_b64,
    get_run as _source_get_run,
    get_run_alerts as _source_get_run_alerts,
    get_run_class_summary as _source_get_run_class_summary,
    get_run_computer_summary as _source_get_run_computer_summary,
    get_run_student_summary as _source_get_run_student_summary,
    list_runs as _source_list_runs,
    run_short_label,
)
from frontend.pages._nav import nav
from frontend.pages.admin_shell import toast
from frontend.pages.design_assets import stylesheet
from frontend.pages.glass_fields import text_field
from frontend.pages.report_helpers import (_duration, _run_csv as _source_run_csv, _pdf_labels)
from frontend.pages._snapshot import make_snapshot_dialogs
from backend.services.report_export import (build_run_pdf as _source_build_run_pdf)
from frontend.translate import t

@ui.page("/reports")
def page_reports() -> None:
    current = require_auth(required_role="teacher")
    if current is None:
        return
    from frontend.pages.teacher_calls import bind
    list_runs = bind(current["id"], _source_list_runs)
    get_run = bind(current["id"], _source_get_run)
    get_run_class_summary = bind(current["id"], _source_get_run_class_summary)
    get_run_student_summary = bind(current["id"], _source_get_run_student_summary)
    get_run_computer_summary = bind(current["id"], _source_get_run_computer_summary)
    get_run_alerts = bind(current["id"], _source_get_run_alerts)
    get_event_frame_b64 = bind(current["id"], _source_get_event_frame_b64)
    get_event_frame_annotated_b64 = bind(current["id"], _source_get_event_frame_annotated_b64)
    _run_csv = bind(current["id"], _source_run_csv)
    from backend.db.run_applications import application_summary
    apps = bind(current["id"],application_summary)
    build_run_pdf = bind(current["id"], _source_build_run_pdf)
    nav(current)
    stylesheet("reports.css")
    list_busy = [False]
    detail_generation = [0]

    with ui.column().classes("reports-dashboard w-full"):
        with ui.column().classes("reports-heading"):
            ui.label(t("reports_title")).classes("reports-title")
            ui.label("Review each monitoring session and download its results.").classes("reports-subtitle")
        with ui.card().classes("reports-toolbar w-full"):
            with ui.element("div").classes("reports-search"):
                search = text_field("Search reports", icon="search", placeholder="Search a date, group or model", props="debounce=200")
            refresh_btn = ui.button(t("reports_refresh"), icon="refresh", on_click=lambda: _load()).props("no-caps")
        ui.label("Showing the latest 200 sessions at most. Search applies to the sessions below.").classes("reports-list-hint")

        cols = [
            {"name": "started_at", "label": t("reports_col_started"),
             "field": "started_at", "sortable": True, "align": "left"},
            {"name": "duration",   "label": t("reports_col_duration"),
             "field": "duration",   "sortable": False, "align": "left"},
            {"name": "trigger",    "label": t("reports_col_trigger"),
             "field": "trigger",    "sortable": True, "align": "left"},
            {"name": "group",      "label": t("reports_col_group"),
             "field": "group",      "sortable": True, "align": "left"},
            {"name": "model",      "label": t("reports_col_model"),
             "field": "model",      "sortable": True, "align": "left"},
            {"name": "computers",  "label": t("reports_col_computers"),
             "field": "computer_count", "sortable": True, "align": "center"},
            {"name": "events",     "label": t("reports_col_events"),
             "field": "total_events",     "sortable": True, "align": "center"},
            {"name": "hits",       "label": t("reports_col_detections"),
             "field": "detection_events", "sortable": True, "align": "center"},
            {"name": "alerts",     "label": t("reports_col_alerts"),
             "field": "alert_count",      "sortable": True, "align": "center"},
            {"name": "status",     "label": t("reports_col_status"),
             "field": "status_label",     "sortable": True, "align": "left"},
            {"name": "actions",    "label": "", "field": "id", "align": "right"},
        ]
        tbl = ui.table(columns=cols, rows=[], row_key="id", pagination={"rowsPerPage": 0}).classes("reports-table w-full")
        tbl.props("flat bordered hide-pagination")
        tbl.bind_filter_from(search, "value")
        tbl.add_slot("no-data", """
            <div class="reports-empty column items-center w-full">
                <q-icon name="description" size="38px" />
                <div class="reports-empty-title">No reports found</div>
                <div>Try another search or start monitoring to create a report.</div>
            </div>
        """)

        tbl.add_slot("body-cell-status", """
            <q-td :props="props">
                <q-badge class="report-status" :class="'report-status--' + props.row.status">
                    {{ props.row.status_label }}
                </q-badge>
            </q-td>""")
        tbl.add_slot("body-cell-actions", """
            <q-td :props="props">
                <q-btn flat no-caps icon="description" class="report-view-button"
                       :aria-label="'Open report ' + props.row.id" :label="props.row._view_label"
                       @click="$parent.$emit('view', props.row)" />
            </q-td>""")

        count_lbl = ui.label("").classes("reports-count").props("role=status aria-live=polite")

        # ── Snapshot viewer (shared dialogs, same as the notification bell) ────
        _snap_dlg, _fs_dlg, show_snapshot = make_snapshot_dialogs()

        # ── Report detail dialog ───────────────────────────────────────────────
        # The card has a DEFINITE height; detail_body is a flex child with
        # min-height:0 + overflow-y:auto so the collapsible sections get the
        # remaining space and scroll. (A bare `flex:1` against a max-height-only
        # parent collapses to zero — which hid the whole report body.)
        with ui.dialog() as detail_dlg, \
             ui.card().classes("report-detail"):
            with ui.row().classes("report-detail-header w-full items-start justify-between"):
                detail_title = ui.label("").classes("report-detail-title")
                ui.button(icon="close", on_click=detail_dlg.close).props('flat round aria-label="Close report"')
            detail_meta = ui.label("").classes("report-detail-meta")
            with ui.column().classes("report-detail-scroll w-full"):
                summary_row = ui.element("div").classes("report-summary-grid w-full")
                detail_body = ui.column().classes("report-detail-body w-full")
            with ui.row().classes("report-detail-footer w-full justify-end gap-3"):
                pdf_btn = ui.button(t("reports_pdf"), icon="picture_as_pdf").props("no-caps disable")
                csv_btn = ui.button(t("reports_csv"), icon="table_view").props("no-caps disable")
                ui.button(t("reports_close"), on_click=detail_dlg.close).props("flat no-caps")

        def _summary_card(label: str, value) -> None:
            with summary_row:
                with ui.card().classes("report-summary-card"):
                    ui.label(str(value)).classes("report-summary-value")
                    ui.label(label).classes("report-summary-label")

        def _breakdown_table(title: str, columns: list[dict],
                             rows: list[dict]) -> None:
            """Collapsible breakdown section (collapsed by default)."""
            with detail_body:
                with ui.expansion(f"{title}  ({len(rows)})", icon="table_chart") \
                        .classes("report-expansion w-full"):
                    if not rows:
                        ui.label(t("reports_no_detections")).classes(
                            "text-xs text-gray-500")
                        return
                    sub = ui.table(columns=columns, rows=rows).classes("w-full")
                    sub.props("flat bordered hide-bottom" if len(rows) <= 10 else "flat bordered")

        async def _view_alert_shot(alert: dict | None) -> None:
            if alert is None:
                return
            raw_b64 = await run.io_bound(get_event_frame_b64, alert["event_id"])
            if not raw_b64:
                toast(t("reports_no_screenshot"), type="warning")
                return
            ann_b64 = await run.io_bound(get_event_frame_annotated_b64, alert["event_id"])
            meta = (f"{alert['class_name']}  •  {alert['computer']}"
                    f"  •  {alert['student']}  •  {alert['created_at']}")
            show_snapshot(raw_b64, meta, ann_b64)

        _ALERT_COLS = [
            {"name": "created_at", "label": t("reports_col_time"),
             "field": "created_at", "sortable": True, "align": "left"},
            {"name": "computer",   "label": t("reports_col_computer"),
             "field": "computer",   "sortable": True, "align": "left"},
            {"name": "student",    "label": t("reports_col_student"),
             "field": "student",    "sortable": True, "align": "left"},
            {"name": "shot",       "label": "", "field": "id", "align": "right"},
        ]

        def _alerts_section(alerts: list[dict]) -> None:
            """
            Prohibited-class alerts, grouped into one collapsible panel per
            class: when each alert fired, on which computer, which student
            caused it, and a button to view the stored screenshot.
            """
            with detail_body:
                with ui.expansion(
                    f'{t("reports_alerts_section")}  ({len(alerts)})',
                    icon="notification_important", value=bool(alerts),
                ).classes("report-expansion w-full"):
                    if not alerts:
                        ui.label(t("reports_alerts_empty")).classes(
                            "text-xs text-gray-500")
                        return
                    by_class: dict[str, list[dict]] = {}
                    for a in alerts:
                        by_class.setdefault(a["class_name"], []).append(a)
                    for cls_name, items in sorted(
                        by_class.items(), key=lambda kv: -len(kv[1])
                    ):
                        students = sorted({a["student"] for a in items})
                        header = (f"{cls_name} — {len(items)} × "
                                  f"({', '.join(students)})")
                        with ui.expansion(header, icon="warning").classes(
                            "w-full"
                        ).style(
                            "border-left: 2px solid #ffffff30"
                        ):
                            atbl = ui.table(
                                columns=_ALERT_COLS, rows=items, row_key="id",
                            ).classes("w-full")
                            atbl.props("flat bordered hide-bottom" if len(items) <= 10 else "flat bordered")
                            atbl.add_slot("body-cell-shot", """
                                <q-td :props="props">
                                    <q-btn v-if="props.row.has_frame" flat round icon="image"
                                           :aria-label="'View alert screenshot ' + props.row.id"
                                           @click="$parent.$emit('shot', props.row)" />
                                </q-td>""")
                            atbl.on("shot", lambda e, alerts=items: _view_alert_shot(next(
                                (a for a in alerts if a["id"] == e.args.get("id")), None)))

        # Export buttons are bound once; they always export the run whose
        # report is currently open (re-binding per open would stack handlers).
        _open_run_id: list[int | None] = [None]

        async def _export(button, kind):
            rid = _open_run_id[0]
            if rid is None or button._props.get("loading"):
                return
            button.props("loading")
            try:
                if kind == "pdf":
                    labels = _pdf_labels()
                    data = await run.io_bound(build_run_pdf, rid, labels)
                else:
                    data = await run.io_bound(_run_csv, rid)
                if data is None:
                    toast(t("reports_not_found"), type="warning")
                    return
                filename = f"monitoring-run-{rid}-" + ("report.pdf" if kind == "pdf" else "detections.csv")
                ui.download(data, filename)
            except Exception:
                logging.getLogger(__name__).exception("Report export failed")
                toast("The download could not be prepared. Please try again.", type="negative")
            finally:
                button.props(remove="loading")

        async def _download_csv():
            await _export(csv_btn, "csv")

        async def _download_pdf():
            await _export(pdf_btn, "pdf")

        csv_btn.on_click(_download_csv)
        pdf_btn.on_click(_download_pdf)

        def _load_detail(run_id):
            result = get_run(run_id)
            if result is None:
                return None
            return (result, get_run_alerts(run_id), get_run_class_summary(run_id),
                    get_run_student_summary(run_id), get_run_computer_summary(run_id), apps(run_id))

        def _detail_closed(e):
            if not e.value:
                detail_generation[0] += 1
                _open_run_id[0] = None

        detail_dlg.on_value_change(_detail_closed)

        async def _open_report(run_id: int) -> None:
            detail_generation[0] += 1
            generation = detail_generation[0]
            _open_run_id[0] = None
            pdf_btn.props("disable")
            csv_btn.props("disable")
            detail_title.set_text("Loading report...")
            detail_meta.set_text("")
            summary_row.clear()
            detail_body.clear()
            with detail_body:
                for _ in range(4):
                    ui.skeleton().classes("report-loading w-full")
            detail_dlg.open()
            try:
                payload = await run.io_bound(_load_detail, run_id)
            except Exception:
                logging.getLogger(__name__).exception("Report detail failed")
                if generation == detail_generation[0]:
                    detail_dlg.close()
                    toast("The report could not load. Please try again.", type="negative")
                return
            if generation != detail_generation[0]:
                return
            if payload is None:
                detail_dlg.close()
                toast(t("reports_not_found"), type="warning")
                return
            report_run, alerts, cls_rows, stu_rows, comp_rows, app_rows = payload
            _open_run_id[0] = run_id

            trigger = (
                t("reports_trigger_schedule").format(
                    name=report_run.get("schedule_name") or "—")
                if report_run["trigger_type"] == "schedule"
                else t("reports_trigger_manual")
            )
            started_by = report_run.get("started_by_name")
            meta_parts = [
                f"{report_run['started_at']} → {report_run.get('ended_at') or '…'}",
                t("reports_col_duration") + ": " +
                _duration(report_run["started_at"], report_run.get("ended_at")),
                trigger,
                report_run.get("group_name") or t("reports_all_computers"),
                report_run.get("model_name") or "—",
            ]
            if started_by:
                meta_parts.append(
                    t("reports_started_by").format(name=started_by))

            detail_title.set_text(
                t("reports_detail_title").format(
                    label=run_short_label(report_run, t("reports_run_word"))))
            detail_meta.set_text("  •  ".join(meta_parts))

            summary_row.clear()
            _summary_card(t("reports_sum_events"),
                          report_run["total_events"])
            _summary_card(t("reports_sum_hits"),
                          report_run["detection_events"])
            _summary_card(t("reports_sum_alerts"),
                          report_run["alert_count"])
            _summary_card(t("reports_sum_students"),
                          report_run["student_count"])
            _summary_card(t("reports_col_computers"),
                          report_run["computer_count"])

            detail_body.clear()

            _alerts_section(alerts)
            _breakdown_table("Windows applications used",[
                {"name":"application","label":"Windows app","field":"application","align":"left"},
                {"name":"samples","label":"Recorded samples","field":"samples","align":"center"}],app_rows)

            for r in cls_rows:
                r["avg_conf"] = f"{r['avg_conf']:.0%}"
                r["share"]    = f"{r['pct']:.1f}%"
            _breakdown_table(t("reports_by_class"), [
                {"name": "name",     "label": t("reports_col_class"),
                 "field": "name",     "sortable": True, "align": "left"},
                {"name": "cnt",      "label": t("reports_col_count"),
                 "field": "cnt",      "sortable": True, "align": "center"},
                {"name": "share",    "label": t("reports_col_share"),
                 "field": "share",    "sortable": True, "align": "center"},
                {"name": "avg_conf", "label": t("reports_col_avg_conf"),
                 "field": "avg_conf", "sortable": True, "align": "center"},
            ], cls_rows)

            _breakdown_table(t("reports_by_student"), [
                {"name": "student", "label": t("reports_col_student"),
                 "field": "student", "sortable": True, "align": "left"},
                {"name": "frames",  "label": t("reports_col_frames"),
                 "field": "frames",  "sortable": True, "align": "center"},
                {"name": "hits",    "label": t("reports_col_detections"),
                 "field": "hits",    "sortable": True, "align": "center"},
                {"name": "classes", "label": t("reports_col_classes"),
                 "field": "classes", "sortable": False, "align": "left"},
            ], stu_rows)

            _breakdown_table(t("reports_by_computer"), [
                {"name": "computer", "label": t("reports_col_computer"),
                 "field": "computer", "sortable": True, "align": "left"},
                {"name": "frames",   "label": t("reports_col_frames"),
                 "field": "frames",   "sortable": True, "align": "center"},
                {"name": "hits",     "label": t("reports_col_detections"),
                 "field": "hits",     "sortable": True, "align": "center"},
            ], comp_rows)

            pdf_btn.props(remove="disable")
            csv_btn.props(remove="disable")

        async def _load() -> None:
            if list_busy[0]:
                return
            list_busy[0] = True
            refresh_btn.props("loading")
            tbl.props("loading")
            try:
                rows = await run.io_bound(list_runs, limit=200)
            except Exception:
                logging.getLogger(__name__).exception("Report list failed")
                toast("Reports could not load. Please try again.", type="negative")
                return
            finally:
                list_busy[0] = False
                refresh_btn.props(remove="loading")
                tbl.props(remove="loading")
            for r in rows:
                r["duration"] = _duration(r["started_at"], r.get("ended_at"))
                r["trigger"] = (
                    t("reports_trigger_schedule").format(
                        name=r.get("schedule_name") or "—")
                    if r["trigger_type"] == "schedule"
                    else t("reports_trigger_manual")
                )
                r["group"]         = r.get("group_name") or t("reports_all_computers")
                r["model"]         = r.get("model_name") or "—"
                r["status_label"]  = t(f"reports_status_{r['status']}")
                r["_view_label"]   = t("reports_view")
            tbl.rows = rows
            tbl.update()
            count_lbl.set_text(t("reports_entries").format(n=len(rows)) + " loaded")
            if not rows:
                count_lbl.set_text(t("reports_empty"))

        tbl.on("view", lambda e: _open_report(int(e.args["id"])))

        ui.timer(0.01, _load, once=True)
