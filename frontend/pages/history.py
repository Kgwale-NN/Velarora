"""
frontend/pages/history.py
────────────────────
History page  /history

Teacher view  — full filters (computer, student, class, hits-only)
Student view  — auto-filtered to own records, computer selector hidden
Both views    — 📷 opens snapshot preview; ⛶ Full screen opens maximized dialog.
Paginated     — records loaded in configurable page sizes (50 / 100 / 200).
"""
import asyncio

from nicegui import run, ui

from backend.core.auth import require_auth
from backend.db.database import (
    count_query_events,
    get_event_frame_b64,
    get_event_frame_annotated_b64,
    list_classes,
    list_computers,
    list_users,
    query_events,
)
from frontend.pages._nav import nav
from frontend.pages.admin_shell import toast
from frontend.pages.design_assets import stylesheet
from frontend.pages.glass_fields import select_field
from frontend.pages._snapshot import make_snapshot_dialogs
from frontend.translate import t


@ui.page("/history")
async def page_history() -> None:
    current = require_auth()
    if current is None:
        return
    nav(current)
    is_teacher = current["role"] == "teacher"
    stylesheet("history.css")

    _snap_dlg, _fs_dlg, show_snapshot = make_snapshot_dialogs()

    # Mutable pagination state
    state = {"page": 0, "has_next": False, "total": None, "busy": False,
             "generation": 0, "page_size": 100, "filters": {}, "shown": 0}

    with ui.column().classes("history-dashboard w-full"):
        with ui.column().classes("history-heading"):
            ui.label(t("history_title") if is_teacher else t("history_my_title")).classes("history-title")
            ui.label("Review screen activity, filter records, and open saved screenshots.").classes("history-subtitle")

        with ui.card().classes("history-filters w-full"):
            with ui.row().classes("items-center gap-3"):
                ui.icon("tune").classes("history-section-icon")
                ui.label("Find activity").classes("history-section-title")
            with ui.element("div").classes("history-filter-grid w-full"):
                if is_teacher:
                    computers = {"": t("history_all_computers")}
                    computers.update({str(c["id"]): c["name"] for c in list_computers()})
                    f_computer = select_field(t("history_computer"), computers, value="", icon="computer")
                    students = {"": t("history_all_students")}
                    students.update({str(u["id"]): u["username"] for u in list_users() if u["role"] == "student"})
                    f_student = select_field(t("history_student"), students, value="", icon="person_outline")
                classes = {"": t("history_all_classes")}
                classes.update({c["name"]: c["name"] for c in list_classes()})
                f_class = select_field(t("history_class"), classes, value="", icon="category")
                f_page_size = select_field(t("history_page_size"), {50: "50", 100: "100", 200: "200"}, value=100, icon="format_list_numbered")
            with ui.row().classes("history-filter-actions w-full items-center justify-between"):
                f_only_hits = ui.checkbox(t("history_detections_only"), value=False).props("color=white keep-color")
                search_btn = ui.button("Search", icon="search", on_click=lambda: _load_page(0)).props("no-caps")

        # ── Table ─────────────────────────────────────────────────────────────
        base_cols = [
            {"name": "detected_at",    "label": t("history_col_time"),
             "field": "detected_at",   "sortable": True,  "align": "left"},
            {"name": "had_detection",  "label": t("history_col_hit"),
             "field": "had_detection", "sortable": True,  "align": "center"},
            {"name": "foreground_app", "label": t("history_windows_app"),
             "field": "foreground_app", "align": "left"},
            {"name": "detections",     "label": t("history_col_detections"),
             "field": "detections",    "sortable": False, "align": "left"},
            {"name": "snapshot",       "label": "Screenshot",
             "field": "has_frame",     "sortable": False, "align": "center"},
        ]
        if is_teacher:
            teacher_cols = [
                {"name": "computer",   "label": t("history_col_computer"),
                 "field": "computer",   "sortable": True, "align": "left"},
                {"name": "student",    "label": t("history_student"),
                 "field": "student",    "sortable": True, "align": "left"},
                {"name": "model_name", "label": t("history_col_model"),
                 "field": "model_name", "sortable": True, "align": "left"},
            ]
            cols = [base_cols[0]] + teacher_cols + base_cols[1:]
        else:
            cols = base_cols

        with ui.row().classes("history-results-heading w-full items-center gap-3"):
            ui.icon("history").classes("history-section-icon")
            ui.label("Activity records").classes("history-section-title")
        tbl = ui.table(columns=cols, rows=[], row_key="event_id", pagination={"rowsPerPage": 0}).classes("history-table w-full")
        tbl.props("flat bordered hide-pagination")
        tbl.add_slot("no-data", """
            <div class="history-empty w-full column items-center">
                <q-icon name="manage_search" size="38px" />
                <div class="history-empty-title">No activity found</div>
                <div>Try different filters or start monitoring to collect records.</div>
            </div>
        """)
        tbl.add_slot("body-cell-had_detection", """
            <q-td :props="props">
                <q-icon v-if="props.row.had_detection" name="check_circle_outline"
                    class="history-hit" aria-label="Detection recorded" size="21px" />
                <span v-else class="history-muted">—</span>
            </q-td>
        """)

        tbl.add_slot("body-cell-snapshot", """
            <q-td :props="props">
                <q-btn v-if="props.row.has_frame"
                    flat round icon="image" class="history-snapshot-button"
                    :aria-label="'View screenshot ' + props.row.event_id"
                    @click="$parent.$emit('view_frame', props.row)"
                />
                <span v-else class="text-gray-600">—</span>
            </q-td>
        """)

        # ── Pagination bar ────────────────────────────────────────────────────
        with ui.row().classes("history-pagination w-full items-center justify-center gap-3"):
            prev_btn = ui.button(icon="chevron_left",
                                 on_click=lambda: _go_page(state["page"] - 1)
                                 ).props('flat round aria-label="Previous page"')
            count_lbl = ui.label("").classes("history-page-count").props('role=status aria-live=polite')
            next_btn  = ui.button(icon="chevron_right",
                                  on_click=lambda: _go_page(state["page"] + 1)
                                  ).props('flat round aria-label="Next page"')

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _filter_kwargs() -> dict:
        comp_id  = None
        user_id_ = None
        if is_teacher:
            comp_id  = int(f_computer.value) if f_computer.value else None
            user_id_ = int(f_student.value)  if f_student.value  else None
        else:
            user_id_ = current["id"]
        return dict(
            computer_id=comp_id,
            user_id=user_id_,
            class_name=f_class.value or "",
            only_hits=bool(f_only_hits.value),
        )

    def _format_count_lbl(n_shown: int) -> None:
        page      = state["page"]
        page_size = state["page_size"]
        first     = page * page_size + 1 if n_shown else 0
        last      = page * page_size + n_shown if n_shown else 0
        total     = state["total"]
        if total is None:
            # count still loading — show range with + indicator
            suffix = "+" if state["has_next"] else ""
            count_lbl.set_text(
                t("history_page_info").format(
                    first=first, last=last, suffix=suffix, page=page + 1,
                )
            )
        else:
            pages = max(1, (total + page_size - 1) // page_size)
            count_lbl.set_text(
                t("history_page_info_total").format(
                    first=first, last=last, total=total,
                    page=page + 1, pages=pages,
                )
            )
        prev_btn.props("disable") if page == 0 else prev_btn.props(remove="disable")
        next_btn.props("disable") if not state["has_next"] else next_btn.props(remove="disable")

    async def _load_page(page: int) -> None:
        if state["busy"]:
            return
        state["busy"] = True
        state["page"] = page
        state["generation"] += 1
        generation = state["generation"]
        if page == 0:
            state["filters"] = _filter_kwargs()
            state["page_size"] = int(f_page_size.value)
            state["total"] = None
        search_btn.props("loading")
        tbl.props("loading")
        prev_btn.props("disable")
        next_btn.props("disable")
        try:
            page_size = state["page_size"]
            kwargs = dict(state["filters"])
            loop      = asyncio.get_event_loop()

            # Fetch one extra row to detect whether a next page exists —
            # no separate COUNT query needed.
            raw = await loop.run_in_executor(
                None,
                lambda: query_events(
                    **kwargs,
                    limit=page_size + 1,
                    offset=page * page_size,
                ),
            )
            state["has_next"] = len(raw) > page_size
            rows = raw[:page_size]

            for r in rows:
                r["student"]       = r["student"]    or "—"
                r["detections"]    = r["detections"] or "—"
                r["model_name"]    = r.get("model_name") or "—"
                r["foreground_app"] = r.get("foreground_app") or "—"
            tbl.rows = rows
            tbl.update()
            state["shown"] = len(rows)
            _format_count_lbl(len(rows))
            # Keep the query's filters and generation: late counts cannot overwrite a new search.
            if state["total"] is None:
                asyncio.create_task(_fetch_total_bg(kwargs, generation))
        finally:
            state["busy"] = False
            search_btn.props(remove="loading")
            tbl.props(remove="loading")
            _format_count_lbl(state["shown"])

    async def _fetch_total_bg(kwargs: dict, generation: int) -> None:
        total = await run.io_bound(count_query_events, **kwargs)
        if generation != state["generation"]:
            return
        state["total"] = total
        _format_count_lbl(state["shown"])

    async def _go_page(page: int) -> None:
        await _load_page(max(0, page))

    # ── Event handlers ────────────────────────────────────────────────────────

    async def handle_view_frame(e) -> None:
        # Only open an event from this user's currently displayed, authorized results.
        eid = e.args.get("event_id") if isinstance(e.args, dict) else None
        row = next((r for r in tbl.rows if r["event_id"] == eid), None)
        if row is None:
            return
        raw_b64 = await run.io_bound(get_event_frame_b64, int(eid))
        if raw_b64:
            ann_b64 = await run.io_bound(get_event_frame_annotated_b64, int(eid))
            meta = (
                f"{row.get('detected_at', '')}  •  "
                f"{row.get('computer', '—')}  •  "
                f"{row.get('student', '—')}"
            )
            show_snapshot(raw_b64, meta, ann_b64)
        else:
            toast(t("history_no_snapshot"), type="info")

    tbl.on("view_frame", handle_view_frame)

    await _load_page(0)
