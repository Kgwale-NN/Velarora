"""Model queries operations."""
from __future__ import annotations
import json
from typing import Optional
from backend.db._core import _conn


def get_active_model() -> Optional[dict]:
    c = _conn()
    row = c.execute(
        "SELECT * FROM ml_model WHERE is_active = 1 LIMIT 1"
    ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["class_names"] = json.loads(d.get("classes_json", "[]"))
    return d


def get_model_by_id(model_id: int) -> Optional[dict]:
    c = _conn()
    row = c.execute(
        "SELECT * FROM ml_model WHERE id = ?", (model_id,)
    ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["class_names"] = json.loads(d.get("classes_json", "[]"))
    return d


def list_models() -> list[dict]:
    """Return all models ordered by creation date, newest first."""
    c = _conn()
    rows = c.execute(
        "SELECT * FROM ml_model ORDER BY created_at DESC"
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["class_names"] = json.loads(d.get("classes_json", "[]"))
        result.append(d)
    return result


def get_class_ids_for_model(model_id: int) -> list[int]:
    """Return the detection_class IDs that belong to this model (via model_class)."""
    c = _conn()
    rows = c.execute(
        "SELECT class_id FROM model_class WHERE model_id = ?", (model_id,)
    ).fetchall()
    return [r[0] for r in rows]
