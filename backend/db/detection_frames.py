"""Detection frames operations."""
from __future__ import annotations
import base64
from typing import Optional
from backend.db._core import _conn
from backend.db.teacher_scope import event_scope


def get_event_frame_b64(event_id: int) -> Optional[str]:
    """Return the stored raw (unannotated) frame as a base64 JPEG data-URL, or None."""
    c = _conn()
    scope, params = event_scope()
    row = c.execute(
        f"SELECT frame_blob FROM detection_event WHERE id = ? AND {scope}", [event_id]+params
    ).fetchone()
    if row and row["frame_blob"]:
        b64 = base64.b64encode(bytes(row["frame_blob"])).decode()
        return f"data:image/jpeg;base64,{b64}"
    return None


def get_event_frame_annotated_b64(event_id: int) -> Optional[str]:
    """
    Re-draw bounding boxes from the detection table onto the stored raw frame
    and return the result as a base64 JPEG data-URL.
    Returns None if no frame is stored or if the frame cannot be decoded.
    """
    c = _conn()
    scope, params = event_scope()
    row = c.execute(
        f"SELECT frame_blob FROM detection_event WHERE id = ? AND {scope}", [event_id]+params
    ).fetchone()
    if not row or not row["frame_blob"]:
        return None

    dets = c.execute("""
        SELECT d.box_x1, d.box_y1, d.box_x2, d.box_y2,
               dc.color_hex, dc.name, d.confidence
        FROM   detection d
        JOIN   detection_class dc ON dc.id = d.class_id
        WHERE  d.event_id = ?
    """, (event_id,)).fetchall()

    import os
    if os.environ.get('VELARORA_CLOUD_DEMO') == 'true':
        from backend.core.frame_annotations import annotate_jpeg
        return annotate_jpeg(bytes(row['frame_blob']), dets)

    import cv2 as _cv2
    import numpy as _np
    from backend.core.colors import hex_to_bgr
    arr = _np.frombuffer(bytes(row["frame_blob"]), dtype=_np.uint8)
    img = _cv2.imdecode(arr, _cv2.IMREAD_COLOR)
    if img is None:
        return None

    for x1, y1, x2, y2, color_hex, label, conf in dets:
        color = hex_to_bgr(color_hex)
        _cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        text = f"{label} {conf:.0%}"
        (tw, th), _ = _cv2.getTextSize(text, _cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        _cv2.rectangle(img, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1)
        _cv2.putText(img, text, (x1 + 2, y1 - 4),
                     _cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1,
                     _cv2.LINE_AA)

    ok, buf = _cv2.imencode(".jpg", img, [_cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ok:
        return None
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()
