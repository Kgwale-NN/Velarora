"""New alerts are tracked by arrival ID, independently of changing unread totals."""
import pytest
from backend.db import _core, schema
from backend.db.notifications import (insert_notification,list_notifications,
    mark_read,mark_all_read,notification_status)


@pytest.fixture
def alerts(tmp_path,monkeypatch):
    monkeypatch.setattr(_core,'DB_PATH',tmp_path/'alerts.db')
    monkeypatch.setattr(schema,'DB_PATH',tmp_path/'alerts.db')
    schema.init_db()
    return _core._conn()


def test_new_arrival_is_found_even_when_unread_total_stays_same(alerts):
    first=insert_notification(None,None)
    before=notification_status()
    mark_read(first)
    second=insert_notification(None,None)
    after=notification_status()
    assert before['unread']==after['unread']==1
    assert after['latest']>before['latest']
    assert [n['id'] for n in list_notifications(after_id=before['latest'])]==[second]
    mark_all_read()
    assert notification_status()=={'unread':0,'latest':second}
    assert list_notifications(after_id=second)==[]


def test_equal_timestamp_alerts_have_stable_newest_first_order(alerts):
    ids=[insert_notification(None,None) for _ in range(4)]
    alerts.execute("UPDATE notification SET created_at='2026-11-18 10:00:00'")
    alerts.commit()
    assert [n['id'] for n in list_notifications(limit=2)]==ids[::-1][:2]
    assert [n['id'] for n in list_notifications(after_id=ids[1])]==ids[:1:-1]
    assert all(n['has_frame']==0 for n in list_notifications())


def test_empty_status_is_numeric_and_read_actions_are_idempotent(alerts):
    assert notification_status()=={'unread':0,'latest':0}
    mark_read(999)
    mark_all_read()
    assert list_notifications()==[]
