"""Model classes operations."""
from __future__ import annotations
import json
from backend.db._core import _conn, _now
from backend.db.model_queries import get_model_by_id


def sync_classes_from_model(model_id: int) -> None:
    """
    Upsert detection_class rows from a trained model's class list, then
    record the model-specific index mapping in model_class.

    detection_class is keyed by name — two models that share a class name
    reuse the same detection_class row (and its color / notification settings).
    model_class maps each model's raw output index to the correct class row so
    models with identical classes at different indices never corrupt each other.
    """
    from backend.core.colors import class_hex
    model = get_model_by_id(model_id)
    if not model:
        return
    names = model.get("class_names", [])
    c = _conn()
    for i, name in enumerate(names):
        # Upsert detection_class by name (not by index).
        c.execute("""
            INSERT INTO detection_class (name, color_hex, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                color_hex = excluded.color_hex
        """, (name, class_hex(i), _now()))

        dc_id = c.execute(
            "SELECT id FROM detection_class WHERE name = ?", (name,)
        ).fetchone()[0]

        # Record this model's index → class mapping.
        c.execute("""
            INSERT INTO model_class (model_id, class_index, class_id)
            VALUES (?, ?, ?)
            ON CONFLICT(model_id, class_index) DO UPDATE SET
                class_id = excluded.class_id
        """, (model_id, i, dc_id))
    c.commit()


def sync_classes_from_file(model_id: int) -> dict:
    """
    Refresh a model's stored class list and index→class mapping from the names
    embedded in its weight file (the authoritative order used at inference).

    This updates ONLY the model's own metadata — ml_model.classes_json and the
    model_class lookup table. It does NOT modify any previously recorded
    detections; existing detection / detection_event rows are left untouched.
    Use it when a model was imported with a class list that doesn't match the
    file, so future detections are labelled correctly.

    Returns {"ok": bool, "reason": str | None, "names": list[str] | None}.
    ok=False (with a reason) when the file is missing or carries no embedded
    names — the caller should keep the existing list in that case.
    """
    from pathlib import Path
    from backend.core.yolo import read_model_class_names

    model = get_model_by_id(model_id)
    if not model:
        return {"ok": False, "reason": "model_not_found", "names": None}
    path = model.get("onnx_path") or model.get("pt_path")
    if not path or not Path(path).exists():
        return {"ok": False, "reason": "file_missing", "names": None}
    embedded = read_model_class_names(path)
    if not embedded:
        return {"ok": False, "reason": "no_embedded_names", "names": None}

    c = _conn()
    # Replace the class list and rebuild the mapping from scratch (drop any
    # stale higher-index rows from a previous, longer class list first).
    c.execute(
        "UPDATE ml_model SET nc = ?, classes_json = ? WHERE id = ?",
        (len(embedded), json.dumps(embedded), model_id),
    )
    c.execute("DELETE FROM model_class WHERE model_id = ?", (model_id,))
    c.commit()
    sync_classes_from_model(model_id)
    return {"ok": True, "reason": None, "names": embedded}
