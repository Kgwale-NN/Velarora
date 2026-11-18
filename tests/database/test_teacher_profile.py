"""Teacher profile edits keep account identity, sign-in email and permissions unchanged."""
import pytest
from backend.db import _core,schema,database as db
from backend.db.teacher_profile import update_teacher_name
from backend.db.user_queries import verify_password_by_id


@pytest.fixture
def accounts(tmp_path,monkeypatch):
    monkeypatch.setattr(_core,'DB_PATH',tmp_path/'profile.db')
    monkeypatch.setattr(schema,'DB_PATH',tmp_path/'profile.db')
    schema.init_db()
    teacher=db.create_user('Teacher','PreviewSecure123!','teacher',email='teacher@example.test')
    student=db.create_user('Student','PreviewSecure123!','student')
    admin=db.create_user('Admin','PreviewSecure123!','admin')
    return teacher,student,admin


def test_teacher_rename_keeps_identity_email_role_and_password(accounts):
    teacher,_,_=accounts
    before=db.get_user_by_id(teacher)
    assert update_teacher_name(teacher,' New Teacher ')== 'New Teacher'
    after=db.get_user_by_id(teacher)
    for key in ('id','email','role','hashed_password','created_at'):
        assert after[key]==before[key]
    assert verify_password_by_id(teacher,'PreviewSecure123!')['username']=='New Teacher'
    assert verify_password_by_id(teacher,'wrong') is None
    assert _core._conn().execute("SELECT user_id FROM audit_log WHERE action='user.profile_update'").fetchone()[0]==teacher


def test_invalid_and_duplicate_names_leave_teacher_unchanged(accounts):
    teacher,_,_=accounts
    for name in ('','  ','x'*101,'Student','Admin'):
        with pytest.raises(ValueError):
            update_teacher_name(teacher,name)
    assert db.get_user_by_id(teacher)['username']=='Teacher'
    assert _core._conn().execute("SELECT COUNT(*) FROM audit_log WHERE action='user.profile_update'").fetchone()[0]==0
    assert update_teacher_name(teacher,'Corrected')=='Corrected'


def test_only_active_teacher_accounts_can_use_teacher_profile(accounts):
    teacher,student,admin=accounts
    for uid in (student,admin,99999):
        with pytest.raises(ValueError):
            update_teacher_name(uid,'Changed')
    _core._conn().execute('UPDATE user SET is_active=0 WHERE id=?',(teacher,));_core._conn().commit()
    with pytest.raises(ValueError):
        update_teacher_name(teacher,'Changed')
    assert verify_password_by_id(teacher,'PreviewSecure123!') is None
