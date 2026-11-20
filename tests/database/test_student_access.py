"""Even legacy active student accounts stay as monitoring identities, never web users."""
from backend.db import _core, schema, database as db
from backend.db.staff_email import authenticate_login
from backend.db.google_account import google_account


def test_active_student_is_denied_password_and_google_without_losing_records(tmp_path,monkeypatch):
    monkeypatch.setattr(_core,'DB_PATH',tmp_path/'student.db')
    monkeypatch.setattr(schema,'DB_PATH',tmp_path/'student.db')
    schema.init_db()
    uid=db.create_user('Learner','Strong-password1','student',email='learner@gmail.com')
    assert authenticate_login('learner@gmail.com','Strong-password1') is None
    claims={'email':'learner@gmail.com','sub':'student-subject','email_verified':True}
    assert google_account(claims) is None
    row=_core._conn().execute('SELECT google_subject FROM user WHERE id=?',(uid,)).fetchone()
    assert row['google_subject'] is None
    assert db.get_user_by_id(uid)['username']=='Learner'
    assert db.auto_create_student('Learner')==uid
    for role in ('admin','teacher'):
        db.create_user(role,'Strong-password1',role,email=role+'@gmail.com')
        assert authenticate_login(role+'@gmail.com','Strong-password1')['role']==role
        assert google_account(dict(claims,email=role+'@gmail.com',sub=role+'-subject'))['role']==role
