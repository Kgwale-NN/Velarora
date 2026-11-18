"""Assignment saves must preserve other groups and roll back on invalid selections."""
import sqlite3
import pytest
from backend.db import _core, schema
from backend.db.group_membership import set_group_computers
from backend.db.group_updates import create_group, update_group, add_computer_to_group
from backend.db.group_queries import list_computers_in_group
from backend.db.computers import upsert_computer


@pytest.fixture
def group_data(tmp_path, monkeypatch):
    monkeypatch.setattr(_core, 'DB_PATH', tmp_path / 'groups.db')
    monkeypatch.setattr(schema, 'DB_PATH', tmp_path / 'groups.db')
    schema.init_db()
    a, b = create_group('Lab A'), create_group('Lab B')
    x, y = upsert_computer('PC 1', '1'), upsert_computer('PC 2', '2')
    add_computer_to_group(x, a)
    add_computer_to_group(x, b)
    return a, b, x, y


def test_replaces_membership_only_in_selected_group_and_audits_actual_changes(group_data):
    a, b, x, y = group_data
    assert set_group_computers(a, {y}) == (1, 1)
    assert [c['id'] for c in list_computers_in_group(a)] == [y]
    assert [c['id'] for c in list_computers_in_group(b)] == [x]
    assert _core._conn().execute("SELECT detail FROM audit_log WHERE action='group.assign'").fetchone()[0] == '+1/-1 computers'
    assert set_group_computers(a, {y}) == (0, 0)
    assert set_group_computers(a, set()) == (0, 1)
    assert list_computers_in_group(a) == []


def test_invalid_computer_rolls_back_and_leaves_connection_usable(group_data):
    a, _, x, y = group_data
    with pytest.raises(ValueError):
        set_group_computers(a, {y, 99999})
    assert [c['id'] for c in list_computers_in_group(a)] == [x]
    assert _core._conn().execute("SELECT COUNT(*) FROM audit_log WHERE action='group.assign'").fetchone()[0] == 0
    assert set_group_computers(a, {y}) == (1, 1)


def test_duplicate_group_name_can_be_corrected_and_saved(group_data):
    a, _, _, _ = group_data
    with pytest.raises(sqlite3.IntegrityError):
        create_group('Lab A')
    with pytest.raises(sqlite3.IntegrityError):
        update_group(a, 'Lab B')
    update_group(a, 'Renamed')
    assert _core._conn().execute('SELECT name FROM computer_group WHERE id=?', (a,)).fetchone()[0] == 'Renamed'
    with pytest.raises(ValueError):
        update_group(99999, 'Missing')
