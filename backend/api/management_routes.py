"""Administrator management endpoints for the React workspace."""

from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from backend.api.admin_security import administrator, mutation
from backend.api.admin_routes import perform
from backend.db import database as db
from backend.db._core import _conn

router = APIRouter(prefix="/api/admin")
A = Annotated[dict, Depends(administrator)]
W = Annotated[dict, Depends(mutation)]


class TeacherPassword(BaseModel):
    password: str = Field(min_length=12, max_length=128)


@router.put("/users/{uid}/password")
async def reset_teacher_password(uid: int, payload: TeacherPassword, actor: W):
    def save():
        user = db.get_user_by_id(uid)
        if not user or user["role"] != "teacher":
            raise ValueError("Select a teacher account.")
        db.update_password(uid, payload.password)
        db.log_action("user.password_reset", user_id=actor["id"], entity="user", entity_id=uid)

    await perform(save)
    return {"ok": True}


@router.get("/audit")
async def audit(
    actor: A,
    limit: int = Query(200, ge=1, le=1000),
    user_id: int | None = None,
    action: str | None = None,
):
    return await perform(lambda: db.list_audit_log(limit=limit, user_id=user_id, action=action))


def workstation_data():
    return {
        "computers": db.list_computers(),
        "groups": db.list_groups(),
        "agents": [
            dict(r)
            for r in _conn().execute(
                "SELECT ca.computer_id AS id,c.name,ca.last_seen,ca.last_app,ca.enabled FROM computer_agent ca JOIN computer c ON c.id=ca.computer_id ORDER BY c.name"
            )
        ],
    }


@router.get("/workstations")
async def workstations(actor: A):
    return await perform(workstation_data)


class Provision(BaseModel):
    computer_id: int
    server_url: str = Field(max_length=500)


@router.post("/workstations/provision")
async def provision(payload: Provision, actor: W):
    from backend.db.agent_credentials import provision_agent

    parsed = urlparse(payload.server_url)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        from fastapi import HTTPException

        raise HTTPException(400, "Enter a plain server URL.")
    if parsed.scheme != "https" and parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
        from fastapi import HTTPException

        raise HTTPException(400, "Use HTTPS for classroom-network connections.")
    token = await perform(provision_agent, actor["id"], payload.computer_id)
    return {"server_url": payload.server_url.rstrip("/"), "token": token}


def settings_data():
    from backend.config import get_settings, DEFAULTS

    cfg = get_settings()
    numeric = {
        "port",
        "start_wait",
        "interval",
        "img_quality",
        "img_width",
        "detect_conf",
        "detect_iou",
        "batch_max_cuda",
        "batch_max_cpu",
        "alert_threshold",
        "retention_days",
    }
    return {
        **{
            k: (float(cfg.get(k, v)) if k in numeric else cfg.get(k, v))
            for k, v in DEFAULTS.items()
        },
        "logon_password": "",
    }


@router.get("/settings")
async def settings(actor: A):
    return await perform(settings_data)


def update_settings(payload, actor):
    from backend.config import get_settings, save_settings, DEFAULTS

    cfg = get_settings()
    numeric = {
        "port": (1, 65535),
        "start_wait": (0, 300),
        "interval": (0.1, 3600),
        "img_quality": (1, 100),
        "img_width": (320, 8192),
        "detect_conf": (0, 1),
        "detect_iou": (0, 1),
        "batch_max_cuda": (1, 512),
        "batch_max_cpu": (1, 128),
        "alert_threshold": (1, 100),
        "retention_days": (0, 36500),
    }
    for key, value in payload.items():
        if (key not in DEFAULTS and key != "logon_password") or key in (
            "model_path",
            "detect_imgsz",
        ):
            continue
        if key == "logon_password" and not value:
            continue
        if key in numeric:
            lo, hi = numeric[key]
            if (
                key not in ("interval", "detect_conf", "detect_iou")
                and isinstance(value, (int, float))
                and not isinstance(value, bool)
                and value != int(value)
            ):
                raise ValueError("Use a whole number for " + key)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not lo <= value <= hi
            ):
                raise ValueError("Invalid value for " + key)
        elif isinstance(DEFAULTS.get(key), bool) and not isinstance(value, bool):
            raise ValueError("Invalid switch value.")
        elif isinstance(DEFAULTS.get(key, ""), str) and (
            not isinstance(value, str) or len(value) > 2000
        ):
            raise ValueError("Invalid text value.")
        cfg[key] = value
    if cfg["auth_method"] not in ("key", "logon"):
        raise ValueError("Choose key or logon authentication.")
    if cfg["img_fmt"] not in ("jpeg", "png"):
        raise ValueError("Choose JPEG or PNG.")
    save_settings(cfg)
    db.log_action("settings.update", user_id=actor["id"])


@router.put("/settings")
async def save_settings(payload: dict, actor: W):
    await perform(update_settings, payload, actor)
    return {"ok": True}


@router.get("/model-alert-rules")
async def rules(actor: A):
    return await perform(lambda: {"model": db.get_active_model(), "rules": db.list_alert_rules()})


class Rule(BaseModel):
    enabled: bool


@router.put("/model-alert-rules/{cid}")
async def update_rule(cid: int, payload: Rule, actor: W):
    await perform(db.set_alert_rule, cid, payload.enabled)
    return {"ok": True}


@router.get("/models")
async def models(actor: A):
    return await perform(db.list_models)


class EditModel(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    imgsz: int = Field(640, ge=128, le=2048, multiple_of=32)


@router.put("/models/{mid}")
async def edit_model(mid: int, payload: EditModel, actor: W):
    def save():
        if not db.get_model_by_id(mid):
            raise ValueError("Model no longer exists.")
        db.update_ml_model(mid, name=payload.name.strip(), imgsz=payload.imgsz)
        if db.get_model_by_id(mid)["is_active"]:
            from backend.config import apply_active_model

            apply_active_model(mid)
        db.log_action("model.update", user_id=actor["id"], entity="ml_model", entity_id=mid)

    await perform(save)
    return {"ok": True}


@router.post("/models/{mid}/activate")
async def activate(mid: int, actor: W):
    def save():
        model = db.get_model_by_id(mid)
        if (
            not model
            or model["status"] != "ready"
            or not Path(model.get("onnx_path") or "").is_file()
        ):
            raise ValueError("This model needs a valid ONNX file before activation.")
        from backend.config import apply_active_model

        db.set_active_model(mid)
        apply_active_model(mid)

    await perform(save)
    return {"ok": True}


@router.post("/models/{mid}/sync")
async def sync(mid: int, actor: W):
    def save():
        if not db.get_model_by_id(mid):
            raise ValueError("Model no longer exists.")
        return db.sync_classes_from_model(mid)

    await perform(save)
    return {"ok": True}


@router.delete("/models/{mid}")
async def delete_model(mid: int, actor: W):
    def remove():
        from backend.services.classroom_state import registry_lock, rooms

        model = db.get_model_by_id(mid)
        if not model:
            raise ValueError("Model no longer exists.")
        with registry_lock:
            if (
                model["is_active"]
                or any(r.running_model_id == mid for r in rooms.values())
                or db.list_schedules_using_model(mid)
            ):
                raise ValueError(
                    "Change the active model and any linked schedules before deleting this model."
                )
            db.delete_model(mid)
        db.log_action("model.delete", user_id=actor["id"], entity="ml_model", entity_id=mid)

    await perform(remove)
    return {"ok": True}
