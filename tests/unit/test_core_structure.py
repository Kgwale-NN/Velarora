"""Check the core size limit and directory grouping after the module split."""
from pathlib import Path

import pytest

from backend.core.veyon_locations import group_locations


@pytest.mark.parametrize("folder", ["core", "db"])
def test_backend_files_have_at_most_100_lines(folder):
    core = Path(__file__).resolve().parents[2] / "backend" / folder
    oversized = {
        p.name: len(p.read_text(encoding="utf-8").splitlines())
        for p in core.rglob("*.py")
        if len(p.read_text(encoding="utf-8").splitlines()) > 100
    }
    assert not oversized, oversized


@pytest.mark.parametrize("objects, expected", [
    (
        [
            {"Type": 2, "Name": "Lab A", "Uid": "{ABC}"},
            {"Type": 2, "Name": "Lab B", "Uid": "other"},
            {"Type": 3, "Name": "PC", "HostAddress": "host", "ParentUid": "abc"},
        ],
        [{"name": "Lab A", "computers": [{"name": "PC", "host": "host"}]}],
    ),
    (
        [
            {"Type": 3, "HostAddress": "first"},
            {"Type": 1, "Name": "Lab"},
            {"Type": 3, "Name": "PC", "HostAddress": "second"},
        ],
        [{"name": "Lab", "computers": [
            {"name": "first", "host": "first"}, {"name": "PC", "host": "second"},
        ]}],
    ),
    (
        [{"Type": 3, "Name": "Missing host"}, {"Type": 3, "hostAddress": "host"}],
        [{"name": "Imported", "computers": [{"name": "host", "host": "host"}]}],
    ),
])
def test_location_grouping_preserves_fallbacks(objects, expected):
    assert group_locations(objects) == expected
