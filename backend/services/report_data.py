"""Framework-independent report downloads shared by the React API."""

import csv
import io
import json
from pathlib import Path
from backend.db.run_applications import run_activity
from backend.services.report_export import build_run_pdf


def _run_csv(run_id: int) -> bytes:
    """All individual detections of a run as CSV (Excel-friendly UTF-8 BOM)."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(
        [
            "detected_at",
            "computer",
            "student",
            "class",
            "windows_app",
            "confidence",
            "box_x1",
            "box_y1",
            "box_x2",
            "box_y2",
        ]
    )
    for d in run_activity(run_id):
        w.writerow(
            [
                d["detected_at"],
                d["computer"],
                d["student"],
                d["class_name"],
                d["foreground_app"],
                f"{d['confidence']:.3f}" if d["confidence"] is not None else "",
                d["box_x1"],
                d["box_y1"],
                d["box_x2"],
                d["box_y2"],
            ]
        )
    return buf.getvalue().encode("utf-8-sig")


LABEL_KEYS = {
    "title": "reports_detail_title",
    "run_word": "reports_run_word",
    "generated": "reports_generated",
    "period": "reports_period",
    "trigger": "reports_col_trigger",
    "group": "reports_col_group",
    "model": "reports_col_model",
    "status": "reports_col_status",
    "started_by": "reports_lbl_started_by",
    "all_computers": "reports_all_computers",
    "trigger_manual": "reports_trigger_manual",
    "trigger_schedule": "reports_trigger_schedule",
    "status_running": "reports_status_running",
    "status_finished": "reports_status_finished",
    "status_interrupted": "reports_status_interrupted",
    "summary": "reports_summary",
    "sum_events": "reports_sum_events",
    "sum_hits": "reports_sum_hits",
    "sum_alerts": "reports_sum_alerts",
    "sum_students": "reports_sum_students",
    "computers": "reports_col_computers",
    "alerts_section": "reports_alerts_section",
    "time": "reports_col_time",
    "class": "reports_col_class",
    "computer": "reports_col_computer",
    "student": "reports_col_student",
    "by_class": "reports_by_class",
    "count": "reports_col_count",
    "avg_conf": "reports_col_avg_conf",
    "share": "reports_col_share",
    "shots_section": "reports_shots_section",
    "shot_none": "reports_shots_none",
    "by_student": "reports_by_student",
    "frames": "reports_col_frames",
    "detections": "reports_col_detections",
    "classes": "reports_col_classes",
    "by_computer": "reports_by_computer",
}


def export_report(run_id, kind):
    if kind == "csv":
        return _run_csv(run_id)
    if kind != "pdf":
        raise ValueError("Choose PDF or CSV.")
    strings = json.loads(
        (Path(__file__).parents[2] / "frontend/locales/en.json").read_text(encoding="utf-8")
    )
    content = build_run_pdf(
        run_id, {key: strings.get(value, value) for key, value in LABEL_KEYS.items()}
    )
    if content is None:
        raise ValueError("This report no longer exists.")
    return content
