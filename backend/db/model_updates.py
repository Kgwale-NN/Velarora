"""Model updates operations."""
from __future__ import annotations
import json
from typing import Optional
from backend.db._core import _conn, _now


def create_ml_model(
    name:        str,
    nc:          int,
    class_names: list[str],
    pt_path:     Optional[str]   = None,
    onnx_path:   Optional[str]   = None,
    map50:       float           = 0.0,
    map50_95:    float           = 0.0,
    precision:   float           = 0.0,
    recall:      float           = 0.0,
    status:      str             = "ready",
    imgsz:       int             = 640,
    dataset_path:    Optional[str]   = None,
    base_model:      Optional[str]   = None,
    epochs:          Optional[int]   = None,
    batch:           Optional[int]   = None,
    device:          Optional[str]   = None,
    parent_model_id: Optional[int]   = None,
    finetune_lr:     Optional[float] = None,
    finetune_frozen: Optional[int]   = None,
) -> int:
    c = _conn()
    now = _now()
    cur = c.execute(
        "INSERT INTO ml_model "
        "(name, pt_path, onnx_path, nc, classes_json, map50, map50_95, "
        " precision, recall, status, imgsz, "
        " dataset_path, base_model, epochs, batch, device, "
        " parent_model_id, finetune_lr, finetune_frozen, "
        " created_at, finished_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (name, pt_path, onnx_path, nc,
         json.dumps(class_names),
         map50, map50_95, precision, recall,
         status, imgsz,
         dataset_path, base_model, epochs, batch, device,
         parent_model_id, finetune_lr, finetune_frozen,
         now, now),
    )
    c.commit()
    return cur.lastrowid


def update_ml_model(model_id: int, **kwargs) -> None:
    allowed = {
        "name", "pt_path", "onnx_path", "nc", "classes_json",
        "imgsz", "map50", "map50_95", "precision", "recall",
        "status", "finished_at", "is_active",
        "dataset_path", "base_model", "epochs", "batch", "device",
    }
    sets = ", ".join(f"{k}=?" for k in kwargs if k in allowed)
    vals = [v for k, v in kwargs.items() if k in allowed]
    if not sets:
        return
    c = _conn()
    c.execute(f"UPDATE ml_model SET {sets} WHERE id=?", [*vals, model_id])
    c.commit()


def set_active_model(model_id: int) -> None:
    from backend.db.audit import _insert_audit
    c = _conn()
    c.execute("UPDATE ml_model SET is_active = 0")
    c.execute("UPDATE ml_model SET is_active = 1 WHERE id = ?", (model_id,))
    _insert_audit(c, "model.activate", entity="ml_model", entity_id=model_id)
    c.commit()


def delete_model(model_id: int) -> None:
    c = _conn()
    c.execute("DELETE FROM ml_model WHERE id = ?", (model_id,))
    c.commit()
