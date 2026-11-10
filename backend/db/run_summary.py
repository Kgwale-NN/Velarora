"""Run summary operations."""
from __future__ import annotations
from backend.db._core import _conn


def get_run_class_summary(run_id: int) -> list[dict]:
    """
    Per detection class: bounding-box count, that class's share of all
    detections in the run (`pct`, 0–100), and the mean confidence.
    """
    c = _conn()
    rows = c.execute("""
        SELECT dc.name, dc.color_hex,
               COUNT(*)           AS cnt,
               AVG(d.confidence)  AS avg_conf
        FROM detection d
        JOIN detection_event e  ON e.id  = d.event_id
        JOIN detection_class dc ON dc.id = d.class_id
        WHERE e.run_id = ?
        GROUP BY dc.id
        ORDER BY cnt DESC
    """, (run_id,)).fetchall()
    result = [dict(r) for r in rows]
    total = sum(r["cnt"] for r in result)
    for r in result:
        r["pct"] = (100.0 * r["cnt"] / total) if total else 0.0
    return result


def get_run_student_summary(run_id: int) -> list[dict]:
    """Per student: frames captured, frames with detections, classes seen."""
    c = _conn()
    rows = c.execute("""
        SELECT COALESCE(u.username, e.os_username, '(unknown)') AS student,
               COUNT(*)             AS frames,
               SUM(e.had_detection) AS hits
        FROM detection_event e
        LEFT JOIN user u ON u.id = e.user_id
        WHERE e.run_id = ?
        GROUP BY student
        ORDER BY hits DESC, frames DESC
    """, (run_id,)).fetchall()
    result = [dict(r) for r in rows]

    # Distinct detected classes per student, merged in Python — simpler and
    # cheaper than a correlated GROUP_CONCAT subquery per output row.
    cls_rows = c.execute("""
        SELECT COALESCE(u.username, e.os_username, '(unknown)') AS student,
               dc.name AS class_name
        FROM detection d
        JOIN detection_event e  ON e.id  = d.event_id
        JOIN detection_class dc ON dc.id = d.class_id
        LEFT JOIN user u        ON u.id  = e.user_id
        WHERE e.run_id = ?
        GROUP BY student, dc.name
        ORDER BY student, dc.name
    """, (run_id,)).fetchall()
    classes_by_student: dict[str, list[str]] = {}
    for r in cls_rows:
        classes_by_student.setdefault(r["student"], []).append(r["class_name"])
    for entry in result:
        entry["classes"] = ", ".join(classes_by_student.get(entry["student"], []))
    return result


def get_run_computer_summary(run_id: int) -> list[dict]:
    """Per computer: frames captured and frames with detections."""
    c = _conn()
    rows = c.execute("""
        SELECT comp.name           AS computer,
               COUNT(*)            AS frames,
               SUM(e.had_detection) AS hits
        FROM detection_event e
        JOIN computer comp ON comp.id = e.computer_id
        WHERE e.run_id = ?
        GROUP BY comp.id
        ORDER BY hits DESC, frames DESC
    """, (run_id,)).fetchall()
    return [dict(r) for r in rows]
