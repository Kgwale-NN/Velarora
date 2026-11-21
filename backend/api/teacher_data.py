"""Ownership enters inside the executor thread for every teacher data operation."""

from backend.db import database as db
from backend.db.teacher_scope import bind
from backend.db.run_applications import application_summary


def owned(actor, function, *args, **kwargs):
    return bind(actor["id"], function)(*args, **kwargs)


def history(actor, cid, uid, klass, hits, limit, offset):
    def read():
        args = dict(computer_id=cid, user_id=uid, class_name=klass, only_hits=hits)
        return {
            "rows": db.query_events(**args, limit=limit, offset=offset),
            "total": db.count_query_events(**args),
        }

    return owned(actor, read)


def options(actor):
    def read():
        return {
            "computers": db.list_computers(),
            "students": [
                {"id": u["id"], "username": u["username"]}
                for u in db.list_users()
                if u["role"] == "student"
            ],
            "classes": db.list_classes(),
        }

    return owned(actor, read)


def analytics(actor, cid, uid, start, end):
    def read():
        return {
            "summary": db.get_summary_stats(cid, uid, start, end),
            "classes": db.get_class_distribution(cid, uid, start, end),
            "daily": db.get_daily_detections(cid, uid, start, end),
            "students": db.get_student_activity(cid, start, end, user_id=uid),
        }

    return owned(actor, read)


def report(actor, rid):
    def read():
        return {
            "run": db.get_run(rid),
            "alerts": db.get_run_alerts(rid),
            "classes": db.get_run_class_summary(rid),
            "students": db.get_run_student_summary(rid),
            "computers": db.get_run_computer_summary(rid),
            "applications": application_summary(rid),
        }

    return owned(actor, read)


def snapshot(actor, eid):
    def read():
        return {
            "raw": db.get_event_frame_b64(eid),
            "annotated": db.get_event_frame_annotated_b64(eid),
        }

    return owned(actor, read)
