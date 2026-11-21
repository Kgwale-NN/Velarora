"""Bounded, serial browser inference with teacher ownership and latched demo alarms."""
import json
import threading
import time
from backend.db import browser_sessions as sessions
from backend.db._core import _conn
from backend.db.model_queries import get_active_model, get_model_by_id
from backend.db.detection_events import insert_event
from backend.db.notifications import insert_notification
from backend.core import browser_inference as vision

gate = threading.Lock()
last_frame = 0.0


def start(owner):
    with gate:
        model = get_active_model()
        if not model:
            raise ValueError("Ask your administrator to upload and activate your trained ONNX model first.")
        vision.model_session(model)
        return {**sessions.begin(owner, model['id']), "model": model['name'],
                "classes": model['class_names']}


def frame(session_id, owner, encoded, settings):
    global last_frame
    if not gate.acquire(blocking=False):
        raise ValueError("The demo is processing a screen. Please wait for the next capture.")
    try:
        row = sessions.read(session_id, owner)
        if row['status'] != 'running' or row['last_seen'] < time.time() - 120:
            raise ValueError("Screen-sharing session ended. Share your screen again.")
        now = time.monotonic()
        if now - last_frame < .75:
            raise ValueError("Please wait for the next capture.")
        last_frame = now
        model = get_model_by_id(row['model_id'])
        if not model:
            raise ValueError("This exam's model is no longer available. End sharing and ask your administrator.")
        image, clean = vision.open_frame(encoded)
        detections = vision.predict(image, model, float(settings['detect_conf']), float(settings['detect_iou']))
        if settings.get('keep_top1', True):
            best = {}
            for detection in detections:
                cls = detection['class_id']
                if cls not in best or detection['conf'] > best[cls]['conf']:
                    best[cls] = detection
            detections = list(best.values())
        eid = insert_event(row['computer_id'], detections, os_username='Shared browser screen',
                           frame_bytes=clean, model_id=model['id'], run_id=row['run_id'])
        c = _conn()
        rules = {r['class_index']: r['class_id'] for r in c.execute(
            "SELECT mc.class_index,mc.class_id FROM model_class mc JOIN detection_class dc "
            "ON dc.id=mc.class_id WHERE mc.model_id=? AND dc.notification_enabled=1", (model['id'],))}
        blocked = [d for d in detections if d['class_id'] in rules]
        previous = json.loads(row['hits']) if isinstance(row['hits'], str) else {}
        hits = {str(d['class_id']): previous.get(str(d['class_id']), 0) + 1 for d in blocked}
        fired = [int(cls) for cls, count in hits.items()
                 if count >= int(settings.get('alert_threshold', 1)) and row['armed']]
        notification_at = row['notification_at']
        if fired and time.time() - notification_at >= 10:
            for cls in fired:
                insert_notification(eid, rules[cls])
            notification_at = time.time()
        alarm = bool(row['alarm'] or fired)
        armed = not blocked if not row['armed'] or fired else True
        with c:
            c.execute("UPDATE browser_session SET last_seen=?,alarm=?,armed=?,hits=?,notification_at=? WHERE id=?",
                      (time.time(), int(alarm), int(armed), json.dumps(hits), notification_at, session_id))
        return {"detections": detections, "alarm": alarm, "event_id": eid,
                "width": image.width, "height": image.height,
                "blocked": sorted({d['name'] for d in blocked})}
    finally:
        gate.release()


def stop(session_id, owner, alarm_only=False):
    with gate:
        return sessions.silence(session_id, owner) if alarm_only else sessions.end(session_id, owner)
