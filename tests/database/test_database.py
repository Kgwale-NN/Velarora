"""
tests/database/test_database.py
──────────────────────
Unit tests for backend/db/database.py.
Each test gets a fresh isolated DB via the autouse `db` fixture.

Run:  pytest tests/database/test_database.py -v
"""
from __future__ import annotations
import sqlite3
import pytest


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def db(tmp_path, monkeypatch):
    import backend.db.database as m
    import backend.db._core as _core
    # Patch DB_PATH in _core (where _conn() reads it) and on the facade for
    # attribute access compatibility.
    monkeypatch.setattr(_core, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(m,     "DB_PATH", tmp_path / "test.db")
    # Force a fresh connection for this test's thread.
    if hasattr(_core._tls, "conn"):
        try:
            _core._tls.conn.close()
        except Exception:
            pass
        del _core._tls.conn
        del _core._tls.db_path
    m.init_db()
    m.seed_classes()
    return m


# ── Helpers ───────────────────────────────────────────────────────────────────

def _teacher(db, name="admin"):
    db.create_user(name, "Test!9password1", "teacher")
    return db.get_user_by_username(name)


def _student(db, name="jonas", created_by=None):
    db.create_user(name, "Test!9password1", "student", created_by_id=created_by)
    return db.get_user_by_username(name)


def _computer(db, name="PC-01", host="10.0.0.1"):
    return db.upsert_computer(name, host)


DETS = [
    {"class_id": 0, "class_name": "DI",      "conf": 0.92, "box": [0, 0, 10, 10]},
    {"class_id": 2, "class_name": "Narsykle", "conf": 0.85, "box": [5, 5, 50, 50]},
]

# Class names that match DETS indices 0 and 2 — used for model_class setup.
_DETS_CLASS_NAMES = ["DI", "Ekrano nuotraukos", "Narsykle"]


def _model_for_dets(db) -> int:
    """Create a model whose class list resolves DETS class indices, return model_id."""
    model_id = db.create_ml_model(
        name="test-model",
        nc=len(_DETS_CLASS_NAMES),
        class_names=_DETS_CLASS_NAMES,
    )
    db.sync_classes_from_model(model_id)
    return model_id


# ── Schema ────────────────────────────────────────────────────────────────────

class TestSchema:
    def test_all_tables_exist(self, db):
        with sqlite3.connect(db.DB_PATH) as c:
            tables = {r[0] for r in c.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
        assert {"role", "computer", "user", "detection_class",
                "detection_event", "detection"}.issubset(tables)

    def test_role_table_seeded(self, db):
        roles = {r["name"] for r in db.list_roles()}
        assert roles == {"admin", "teacher", "student"}

    def test_get_role_id_known(self, db):
        rid = db.get_role_id("teacher")
        assert isinstance(rid, int) and rid > 0

    def test_get_role_id_unknown_returns_none(self, db):
        assert db.get_role_id("superuser") is None

    def test_detection_event_has_windows_username_col(self, db):
        with sqlite3.connect(db.DB_PATH) as c:
            cols = {r[1] for r in c.execute(
                "PRAGMA table_info(detection_event)"
            )}
        assert "os_username" in cols

    def test_seed_classes_count(self, db):
        assert len(db.list_classes()) == 7

    def test_seed_idempotent(self, db):
        db.seed_classes()
        assert len(db.list_classes()) == 7

    def test_default_admin_created_with_admin_role(self, db):
        """ensure_default_admin creates an admin-role account on an empty DB."""
        db.ensure_default_admin("admin", "Test!9admin-password-1234")
        u = db.get_user_by_username("admin")
        assert u is not None
        assert u["role"] == "admin"

    def test_default_admin_no_duplicate(self, db):
        """Calling ensure_default_admin twice must not create a second account."""
        db.ensure_default_admin("admin", "Test!9admin-password-1234")
        db.ensure_default_admin("admin", "different-password-9876")
        with sqlite3.connect(db.DB_PATH) as c:
            assert c.execute("SELECT COUNT(*) FROM user").fetchone()[0] == 1

    def test_default_admin_requires_credentials(self, db):
        """Empty credentials are rejected — no silent fallback to admin/admin."""
        import pytest
        with pytest.raises(ValueError):
            db.ensure_default_admin("", "")
        with pytest.raises(ValueError):
            db.ensure_default_admin("admin", "")

    def test_migration_safe_on_existing_db(self, db):
        """Running init_db a second time must not crash on an existing schema."""
        db.init_db()
        assert len(db.list_classes()) == 7


# ── Users ─────────────────────────────────────────────────────────────────────

class TestUsers:
    def test_create_and_retrieve(self, db):
        uid = db.create_user("bob", "Test!9password1", "student")
        u = db.get_user_by_id(uid)
        assert u["username"] == "bob" and u["role"] == "student"

    def test_role_string_returned_from_join(self, db):
        """user["role"] must be the role name string, not an integer id."""
        db.create_user("alice", "Test!9password1", "teacher")
        u = db.get_user_by_username("alice")
        assert u["role"] == "teacher"
        assert isinstance(u["role"], str)

    def test_unknown_role_raises(self, db):
        with pytest.raises(ValueError, match="Unknown role"):
            db.create_user("x", "Test!9password1", "superuser")

    def test_duplicate_raises(self, db):
        db.create_user("alice", "Test!9password1", "student")
        with pytest.raises(sqlite3.IntegrityError):
            db.create_user("alice", "Test!9password2", "student")

    def test_verify_correct(self, db):
        db.create_user("carol", "Test!9secret-pass", "teacher")
        assert db.verify_password("carol", "Test!9secret-pass") is not None

    def test_verify_wrong(self, db):
        db.create_user("dave", "Test!9right-pass", "student")
        assert db.verify_password("dave", "wrong") is None

    def test_verify_unknown(self, db):
        assert db.verify_password("ghost", "Test!9password1") is None

    def test_update_password(self, db):
        db.create_user("eve", "Test!9old-pass-123", "student")
        uid = db.get_user_by_username("eve")["id"]
        db.update_password(uid, "Test!9new-pass-123")
        assert db.verify_password("eve", "Test!9new-pass-123")
        assert not db.verify_password("eve", "Test!9old-pass-123")

    def test_delete_user(self, db):
        db.create_user("frank", "Test!9password1", "student")
        uid = db.get_user_by_username("frank")["id"]
        db.delete_user(uid)
        assert db.get_user_by_username("frank") is None

    def test_list_users_returns_role_as_string(self, db):
        db.create_user("u1", "Test!9password1", "teacher")
        db.create_user("u2", "Test!9password1", "student")
        users = {u["username"]: u for u in db.list_users()}
        assert users["u1"]["role"] == "teacher"
        assert users["u2"]["role"] == "student"

    def test_list_users_names(self, db):
        db.create_user("u1", "Test!9password1", "teacher")
        db.create_user("u2", "Test!9password1", "student")
        names = {u["username"] for u in db.list_users()}
        assert {"u1", "u2"} == names

    def test_created_by_stored(self, db):
        t = _teacher(db)
        db.create_user("pupil", "Test!9password1", "student", created_by_id=t["id"])
        u = db.get_user_by_username("pupil")
        assert u["created_by"] == t["id"]


# ── Password policy ───────────────────────────────────────────────────────────

class TestPasswordPolicy:
    """Server-side minimum-length enforcement on every password-setting path."""

    def test_create_user_rejects_short_password(self, db):
        with pytest.raises(ValueError, match="at least"):
            db.create_user("shorty", "a" * (db.MIN_PASSWORD_LENGTH - 1), "student")
        assert db.get_user_by_username("shorty") is None

    def test_create_user_rejects_empty_password(self, db):
        with pytest.raises(ValueError):
            db.create_user("shorty", "", "student")

    def test_create_user_accepts_exact_minimum(self, db):
        uid = db.create_user("okuser", "A1!" + "a" * (db.MIN_PASSWORD_LENGTH - 3), "student")
        assert db.get_user_by_id(uid) is not None

    def test_update_password_rejects_short(self, db):
        uid = db.create_user("bob", "Test!9password1", "student")
        with pytest.raises(ValueError):
            db.update_password(uid, "tiny")
        assert db.verify_password("bob", "Test!9password1") is not None  # unchanged

    def test_activate_user_rejects_short(self, db):
        uid = db.auto_create_student("Jonas")
        with pytest.raises(ValueError):
            db.activate_user(uid, "tiny")
        assert db.get_user_by_id(uid)["is_active"] == 0  # still inactive

    def test_auto_create_student_exempt(self, db):
        """Auto-created placeholders use a random internal password — no policy check."""
        uid = db.auto_create_student("Lina")
        assert db.get_user_by_id(uid) is not None

    # ── PASSWORD_MIN_LENGTH env override ──────────────────────────────────────

    def test_env_min_length_default(self, monkeypatch):
        import backend.db.user_passwords as users_mod
        monkeypatch.delenv("PASSWORD_MIN_LENGTH", raising=False)
        assert users_mod._min_password_length() == 12

    def test_env_min_length_override(self, monkeypatch):
        import backend.db.user_passwords as users_mod
        monkeypatch.setenv("PASSWORD_MIN_LENGTH", "12")
        assert users_mod._min_password_length() == 12

    def test_env_min_length_floor_is_twelve(self, monkeypatch):
        """0 or negative must not disable the not-empty check entirely."""
        import backend.db.user_passwords as users_mod
        monkeypatch.setenv("PASSWORD_MIN_LENGTH", "0")
        assert users_mod._min_password_length() == 12

    def test_env_min_length_garbage_falls_back(self, monkeypatch):
        import backend.db.user_passwords as users_mod
        monkeypatch.setenv("PASSWORD_MIN_LENGTH", "short")
        assert users_mod._min_password_length() == 12

    def test_validate_uses_module_constant(self, db, monkeypatch):
        """validate_password reads MIN_PASSWORD_LENGTH at call time."""
        import backend.db.user_passwords as users_mod
        monkeypatch.setattr(users_mod, "MIN_PASSWORD_LENGTH", 12)
        with pytest.raises(ValueError):
            db.create_user("strictuser", "elevenchars", "student")  # 11 < 12
        db.create_user("strictuser", "Twelve-char1", "student")     # 12 ok


# ── Timing-safe verify_password ───────────────────────────────────────────────

class TestVerifyPasswordTiming:
    """
    The bcrypt comparison must run on EVERY login attempt — unknown username,
    inactive account, or real user alike — so response time can't be used to
    enumerate valid accounts.
    """

    @pytest.fixture()
    def bcrypt_spy(self, monkeypatch):
        import backend.db.user_queries as users_mod
        calls = []
        real = users_mod._verify_pw

        def spy(password, hashed):
            calls.append(hashed)
            return real(password, hashed)

        monkeypatch.setattr(users_mod, "_verify_pw", spy)
        return calls

    def test_unknown_user_still_runs_bcrypt(self, db, bcrypt_spy):
        assert db.verify_password("ghost", "whatever") is None
        assert len(bcrypt_spy) == 1  # dummy-hash comparison happened

    def test_inactive_user_still_runs_bcrypt(self, db, bcrypt_spy):
        db.auto_create_student("Jonas")
        assert db.verify_password("Jonas", "whatever") is None
        assert len(bcrypt_spy) == 1

    def test_inactive_user_with_known_password_rejected(self, db):
        """is_active=0 must block login even when the password matches."""
        uid = db.create_user("frozen", "Test!9password1", "student", is_active=False)
        assert db.get_user_by_id(uid)["is_active"] == 0
        assert db.verify_password("frozen", "Test!9password1") is None

    def test_active_user_unaffected(self, db, bcrypt_spy):
        db.create_user("carol", "Test!9secret-pass", "teacher")
        assert db.verify_password("carol", "Test!9secret-pass") is not None
        assert len(bcrypt_spy) == 1


# ── Computers ─────────────────────────────────────────────────────────────────

class TestComputers:
    def test_upsert_returns_id(self, db):
        cid = _computer(db)
        assert isinstance(cid, int)

    def test_upsert_idempotent(self, db):
        assert _computer(db) == _computer(db)

    def test_list(self, db):
        db.upsert_computer("A", "1.1.1.1")
        db.upsert_computer("B", "1.1.1.2")
        names = {c["name"] for c in db.list_computers()}
        assert {"A", "B"} == names


# ── Detection events ──────────────────────────────────────────────────────────

class TestDetectionEvents:
    def test_insert_with_detections(self, db):
        cid = _computer(db)
        db.insert_event(cid, DETS)
        rows = db.query_events(computer_id=cid)
        assert len(rows) == 1 and rows[0]["had_detection"] == 1

    def test_insert_empty_detections(self, db):
        cid = _computer(db)
        db.insert_event(cid, [])
        rows = db.query_events(computer_id=cid)
        assert len(rows) == 1 and rows[0]["had_detection"] == 0

    def test_windows_username_stored(self, db):
        cid = _computer(db)
        db.insert_event(cid, [], os_username="Jonas")
        with sqlite3.connect(db.DB_PATH) as c:
            row = c.execute(
                "SELECT os_username FROM detection_event"
            ).fetchone()
        assert row[0] == "Jonas"

    def test_windows_username_shown_when_no_account(self, db):
        cid = _computer(db)
        db.insert_event(cid, DETS, os_username="Jonas")
        rows = db.query_events(computer_id=cid)
        assert rows[0]["student"] == "Jonas"

    def test_frame_blob_round_trip(self, db):
        cid   = _computer(db)
        frame = b"\xff\xd8\xff" + b"\xaa" * 50
        eid   = db.insert_event(cid, [], frame_bytes=frame)
        b64   = db.get_event_frame_b64(eid)
        assert b64 and b64.startswith("data:image/jpeg;base64,")

    def test_no_blob_returns_none(self, db):
        cid = _computer(db)
        eid = db.insert_event(cid, [])
        assert db.get_event_frame_b64(eid) is None

    def test_user_linked_when_provided(self, db):
        cid = _computer(db)
        s   = _student(db)
        db.insert_event(cid, DETS, user_id=s["id"])
        rows = db.query_events(user_id=s["id"])
        assert len(rows) == 1 and rows[0]["student"] == "jonas"

    def test_results_ordered_desc(self, db):
        cid = _computer(db)
        for _ in range(3):
            db.insert_event(cid, [])
        times = [r["detected_at"] for r in db.query_events(computer_id=cid)]
        assert times == sorted(times, reverse=True)


# ── Query filters ─────────────────────────────────────────────────────────────

class TestQueryFilters:
    def _setup(self, db):
        c1  = db.upsert_computer("PC-01", "10.0.0.1")
        c2  = db.upsert_computer("PC-02", "10.0.0.2")
        s   = _student(db)
        mid = _model_for_dets(db)
        db.insert_event(c1, DETS, user_id=s["id"], os_username="jonas", model_id=mid)
        db.insert_event(c1, [])
        db.insert_event(c2, DETS, model_id=mid)
        return c1, c2, s

    def test_by_computer(self, db):
        c1, _, _ = self._setup(db)
        assert all(r["computer"] == "PC-01"
                   for r in db.query_events(computer_id=c1))

    def test_by_user(self, db):
        _, _, s = self._setup(db)
        rows = db.query_events(user_id=s["id"])
        assert len(rows) == 1 and rows[0]["student"] == "jonas"

    def test_only_hits(self, db):
        c1, _, _ = self._setup(db)
        rows = db.query_events(computer_id=c1, only_hits=True)
        assert len(rows) == 1 and rows[0]["had_detection"] == 1

    def test_by_class_name(self, db):
        c1, _, _ = self._setup(db)
        assert len(db.query_events(computer_id=c1, class_name="DI")) == 1

    def test_limit(self, db):
        cid = _computer(db)
        for _ in range(10):
            db.insert_event(cid, [])
        assert len(db.query_events(computer_id=cid, limit=4)) == 4


# ── Auto-assign on account creation ──────────────────────────────────────────

class TestAutoAssign:
    def test_events_assigned_on_user_creation(self, db):
        cid = _computer(db)
        for _ in range(3):
            db.insert_event(cid, DETS, os_username="Jonas")
        uid = db.create_user("Jonas", "Test!9password1", "student")
        db.auto_assign_user_events("Jonas", uid)
        rows = db.query_events(user_id=uid)
        assert len(rows) == 3

    def test_case_insensitive_match(self, db):
        cid = _computer(db)
        db.insert_event(cid, [], os_username="JONAS")
        uid = db.create_user("jonas", "Test!9password1", "student")
        db.auto_assign_user_events("jonas", uid)
        rows = db.query_events(user_id=uid)
        assert len(rows) == 1

    def test_already_assigned_not_touched(self, db):
        cid   = _computer(db)
        other = _student(db, "other")
        db.insert_event(cid, [], user_id=other["id"], os_username="other")
        db.insert_event(cid, [], os_username="Jonas")
        uid = db.create_user("Jonas", "Test!9password1", "student")
        db.auto_assign_user_events("Jonas", uid)
        assert len(db.query_events(user_id=uid)) == 1

    def test_no_matching_events_is_fine(self, db):
        uid = db.create_user("newbie", "Test!9password1", "student")
        assert isinstance(uid, int)

    def test_count_anonymous_events(self, db):
        cid = _computer(db)
        db.insert_event(cid, [])
        db.insert_event(cid, [])
        assert db.count_anonymous_events(cid) == 2

    def test_manual_assign(self, db):
        cid = _computer(db)
        s   = _student(db)
        db.insert_event(cid, [])
        db.insert_event(cid, [])
        n = db.assign_anonymous_events(s["id"], cid)
        assert n == 2 and db.count_anonymous_events(cid) == 0


def test_all_roles_sign_in_only_by_email(db):
    from backend.db.staff_email import authenticate_login, link_account_email
    for role in ("admin", "teacher", "student"):
        uid = db.create_user(role, "Test!9existing-password", role)
        email = role + "@school.example"
        link_account_email(uid, email)
        user = authenticate_login(email.upper(), "Test!9existing-password")
        assert (user["id"], user["role"], user["username"]) == (uid, role, role)
        assert authenticate_login(role, "Test!9existing-password") is None
        assert authenticate_login(email, "wrong") is None
    uid = db.create_user("New", "Test!9existing-password", "student", is_active=False)
    with pytest.raises(ValueError):
        link_account_email(uid, "Admin@school.example")
    link_account_email(uid, "new@school.example")
    assert authenticate_login("new@school.example", "Test!9existing-password") is None

@pytest.mark.parametrize("value,reason", [
    ("lowercase123!", "capital"),
    ("MissingNumber!", "number"),
    ("MissingSymbol123", "symbol"),
    ("Spaces Only123", "symbol"),
    ("A1!" + "x" * 70, "72 bytes"),
])
def test_new_password_rules(value, reason):
    from backend.db.user_passwords import validate_password
    with pytest.raises(ValueError, match=reason):
        validate_password(value)

def test_google_account_requires_approved_identity(db):
    from backend.db.google_account import google_account
    uid = db.create_user("Principal", "Strong-password1", "admin", email="admin@gmail.com")
    claims = {"email": "ADMIN@gmail.com", "sub": "subject1", "email_verified": True}
    assert google_account(dict(claims, email_verified=False)) is None
    assert google_account(dict(claims, email="unknown@gmail.com")) is None
    assert google_account(claims) == {"id": uid, "username": "Principal", "role": "admin"}
    assert google_account(dict(claims, sub="subject2")) is None
    db.create_user("Tutor", "Strong-password1", "teacher", email="teacher@school.example")
    school = dict(claims, email="teacher@school.example", sub="subject2")
    assert google_account(school) is None
    assert google_account(dict(school, hd="school.example"))["role"] == "teacher"
    db.create_user("Student", "Strong-password1", "student", is_active=False, email="student@gmail.com")
    assert google_account(dict(claims, email="student@gmail.com", sub="subject3")) is None

def test_admin_can_rename_without_changing_identity(db):
    from backend.db.admin_profile import update_admin_name
    uid = db.create_user("Old name", "Strong-password1", "admin", email="admin@example.test")
    assert update_admin_name(uid, " New name ") == "New name"
    user = db.get_user_by_id(uid)
    assert user["username"] == "New name" and user["email"] == "admin@example.test"
    assert db.verify_password("New name", "Strong-password1")
    student = db.create_user("Student", "Strong-password1", "student")
    with pytest.raises(ValueError):
        update_admin_name(student, "Other name")
    with pytest.raises(ValueError):
        update_admin_name(uid, "Student")
    assert db.get_user_by_id(uid)["username"] == "New name"
