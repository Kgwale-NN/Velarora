"""Schedule edits must preserve intended groups, activation, model and alert policy."""
import sqlite3
import pytest
from backend.db import _core, schema, database as db
from backend.db.schedule_editor_save import save_editor_schedule
from backend.db.schedule_updates import create_schedule, update_schedule


@pytest.fixture
def schedule_data(tmp_path,monkeypatch):
    monkeypatch.setattr(_core,'DB_PATH',tmp_path/'schedules.db')
    monkeypatch.setattr(schema,'DB_PATH',tmp_path/'schedules.db')
    schema.init_db()
    a,b=db.create_group('Lab A'),db.create_group('Lab B')
    mid=db.create_ml_model('Model',1,['Notepad'])
    db.sync_classes_from_model(mid)
    db.set_active_model(mid)
    cid=db.get_class_ids_for_model(mid)[0]
    return a,b,mid,cid


def payload(group,**changes):
    return dict(name='Exam',group_id=group,model_id=None,days=['0','1'],start='09:00',end='10:00',
                active=True,custom=False,notify_ids=[]) | changes


def test_create_paused_and_edit_group_without_pinning_active_model(schedule_data):
    a,b,_,_=schedule_data
    sid=save_editor_schedule(payload(a,active=False),None)
    assert db.get_schedule(sid)['is_active']==0
    assert db.get_schedule(sid)['model_id'] is None
    save_editor_schedule(payload(b,active=True),None,sid)
    assert db.get_schedule(sid)['group_id']==b
    assert db.get_schedule(sid)['is_active']==1
    assert db.get_schedule(sid)['model_id'] is None


def test_custom_empty_selection_is_not_global_and_can_be_restored(schedule_data):
    a,_,mid,cid=schedule_data
    db.set_alert_rule(cid,True)
    sid=save_editor_schedule(payload(a,custom=True),None)
    assert db.get_schedule(sid)['use_custom_notify_classes']==1
    assert db.get_prohibited_class_ids(mid,sid)=={}
    save_editor_schedule(payload(a,custom=False),None,sid)
    assert cid in {r['id'] for r in db.get_prohibited_class_ids(mid,sid).values()}


def test_group_change_and_rules_roll_back_together_on_invalid_class(schedule_data):
    a,b,mid,cid=schedule_data
    sid=create_schedule(a,'Original','0','08:00','09:00',model_id=mid,use_custom_notify_classes=True,notify_class_ids=[cid])
    with pytest.raises(sqlite3.IntegrityError):
        update_schedule(sid,'Changed','0','08:00','09:00',False,group_id=b,model_id=mid,
                        use_custom_notify_classes=True,notify_class_ids=[999999])
    stored=db.get_schedule(sid)
    assert (stored['name'],stored['group_id'],stored['is_active'],stored['notify_class_ids'])==('Original',a,1,[cid])
    with pytest.raises(sqlite3.IntegrityError):
        create_schedule(a,'Invalid','0','12:00','13:00',use_custom_notify_classes=True,notify_class_ids=[999999])
    assert len(db.list_schedules())==1


def test_overlap_is_global_adjacent_is_allowed_and_edit_excludes_self(schedule_data):
    a,b,_,_=schedule_data
    sid=save_editor_schedule(payload(a),None)
    with pytest.raises(ValueError,match='Time conflict'):
        save_editor_schedule(payload(b,name='Clash',start='09:30',end='10:30'),None)
    save_editor_schedule(payload(a),None,sid)
    save_editor_schedule(payload(b,name='Next',start='10:00',end='11:00'),None)
    assert len(db.list_schedules())==2


@pytest.mark.parametrize('changes',[{'days':[]},{'start':'9:00'},{'start':'25:00'},{'end':'08:00'},{'name':'  '}])
def test_invalid_values_do_not_write(changes,schedule_data):
    a,_,_,_=schedule_data
    with pytest.raises(ValueError):
        save_editor_schedule(payload(a,**changes),None)
    assert db.list_schedules()==[]


def test_saved_disabled_schedule_is_not_picked_by_scheduler(schedule_data,monkeypatch):
    from datetime import datetime
    import backend.db.schedule_timing as timing
    class Monday(datetime):
        @classmethod
        def now(cls): return cls(2026,11,16,9,30)
    monkeypatch.setattr(timing,'datetime',Monday)
    a,_,_,_=schedule_data
    sid=save_editor_schedule(payload(a,active=False),None)
    assert db.get_active_schedules_now()==[]
    save_editor_schedule(payload(a,active=True),None,sid)
    assert [s['id'] for s in db.get_active_schedules_now()]==[sid]
    save_editor_schedule(payload(a,start='10:00',end='11:00'),None,sid)
    assert db.get_active_schedules_now()==[]
