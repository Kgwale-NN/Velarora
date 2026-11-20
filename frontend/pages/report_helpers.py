"""Report labels, CSV encoding and duration formatting, separate from the page layout."""
import csv
import io
from datetime import datetime
from backend.db.run_applications import run_activity
from frontend.translate import t

_TS_FMT = "%Y-%m-%d %H:%M:%S"

def _duration(started_at: str, ended_at: str | None) -> str:
    """Human-readable run length; live runs measure against now."""
    try:
        start = datetime.strptime(started_at, _TS_FMT)
        end   = datetime.strptime(ended_at, _TS_FMT) if ended_at else datetime.now()
    except (TypeError, ValueError):
        return "—"
    secs = max(0, int((end - start).total_seconds()))
    h, rem = divmod(secs, 3600)
    m, s   = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _run_csv(run_id: int) -> bytes:
    """All individual detections of a run as CSV (Excel-friendly UTF-8 BOM)."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["detected_at", "computer", "student", "class",
                "windows_app", "confidence", "box_x1", "box_y1", "box_x2", "box_y2"])
    for d in run_activity(run_id):
        w.writerow([
            d["detected_at"], d["computer"], d["student"], d["class_name"],
            d["foreground_app"], f"{d['confidence']:.3f}" if d["confidence"] is not None else "",
            d["box_x1"], d["box_y1"], d["box_x2"], d["box_y2"],
        ])
    return buf.getvalue().encode("utf-8-sig")


def _pdf_labels() -> dict[str, str]:
    return {
        "title":              t("reports_detail_title"),
        "run_word":           t("reports_run_word"),
        "generated":          t("reports_generated"),
        "period":             t("reports_period"),
        "trigger":            t("reports_col_trigger"),
        "group":              t("reports_col_group"),
        "model":              t("reports_col_model"),
        "status":             t("reports_col_status"),
        "started_by":         t("reports_lbl_started_by"),
        "all_computers":      t("reports_all_computers"),
        "trigger_manual":     t("reports_trigger_manual"),
        "trigger_schedule":   t("reports_trigger_schedule"),
        "status_running":     t("reports_status_running"),
        "status_finished":    t("reports_status_finished"),
        "status_interrupted": t("reports_status_interrupted"),
        "summary":            t("reports_summary"),
        "sum_events":         t("reports_sum_events"),
        "sum_hits":           t("reports_sum_hits"),
        "sum_alerts":         t("reports_sum_alerts"),
        "sum_students":       t("reports_sum_students"),
        "computers":          t("reports_col_computers"),
        "alerts_section":     t("reports_alerts_section"),
        "time":               t("reports_col_time"),
        "class":              t("reports_col_class"),
        "computer":           t("reports_col_computer"),
        "student":            t("reports_col_student"),
        "by_class":           t("reports_by_class"),
        "count":              t("reports_col_count"),
        "avg_conf":           t("reports_col_avg_conf"),
        "share":              t("reports_col_share"),
        "shots_section":      t("reports_shots_section"),
        "shot_none":          t("reports_shots_none"),
        "by_student":         t("reports_by_student"),
        "frames":             t("reports_col_frames"),
        "detections":         t("reports_col_detections"),
        "classes":            t("reports_col_classes"),
        "by_computer":        t("reports_by_computer"),
    }
