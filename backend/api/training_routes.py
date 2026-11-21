"""Administrator dataset, import and background training API."""

import io
import os
import threading
import uuid
import zipfile
from pathlib import Path
from typing import Annotated
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from pydantic import BaseModel, Field
from backend.api.admin_security import administrator, mutation
from backend.api.admin_routes import perform
from backend.db import database as db
import backend.state as state
from backend.services import training_service as training

router = APIRouter(prefix="/api/admin")
A = Annotated[dict, Depends(administrator)]
W = Annotated[dict, Depends(mutation)]
lock = threading.Lock()


@router.get("/training")
async def status(actor: A):
    worker = state.training_worker
    return {
        "hardware": await perform(training.get_torch_info),
        "bases": training.BASE_MODELS,
        "job": {
            "running": worker.is_running,
            "done": worker.is_done,
            "status": worker.current_status,
            "batch": worker.batch_progress,
            "epochs": list(worker.epoch_history),
            "model_id": worker.result_model_id,
            "error": worker.error_message,
        }
        if worker
        else None,
    }


class ServerPath(BaseModel):
    path: str = Field(min_length=1, max_length=2000)


async def bounded_upload(file, limit):
    content = await file.read(limit + 1)
    if len(content) > limit:
        raise HTTPException(413, "This upload is too large. Use a server folder instead.")
    return content


def analyse(path):
    result = training.analyze_dataset(str(Path(path).resolve()))
    if not result.get("ok"):
        raise ValueError(result.get("error", "Dataset could not be analysed."))
    return result


@router.post("/datasets/path")
async def dataset_path(payload: ServerPath, actor: W):
    return await perform(analyse, payload.path)


def extract(content):
    target = training.DATASETS_DIR / ("upload_" + uuid.uuid4().hex)
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        entries = archive.infolist()
        if len(entries) > 50000 or sum(e.file_size for e in entries) > 2 * 1024**3:
            raise ValueError("Dataset exceeds the extraction limit.")
        for entry in entries:
            name = entry.filename.replace("\\", "/")
            destination = (target / name).resolve()
            if (
                ":" in name
                or not destination.is_relative_to(target.resolve())
                or ((entry.external_attr >> 16) & 0o170000) == 0o120000
            ):
                raise ValueError("The ZIP contains an unsafe file path.")
        target.mkdir(parents=True)
        archive.extractall(target)
    return analyse(target)


@router.post("/datasets/upload")
async def dataset_upload(actor: W, file: Annotated[UploadFile, File()]):
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(400, "Upload a dataset ZIP.")
    return await perform(extract, await bounded_upload(file, 256 * 1024**2))


class Train(BaseModel):
    dataset_path: str = Field(min_length=1, max_length=2000)
    base_model: str = "yolov5n.pt"
    epochs: int = Field(30, ge=1, le=1000)
    imgsz: int = Field(640, ge=128, le=2048, multiple_of=32)
    batch: int = Field(4, ge=1, le=128)
    name: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    source_id: int | None = None
    learning_rate: float = Field(0.001, gt=0, le=0.1)
    freeze_backbone: bool = False
    extend_classes: bool = False


def begin(payload, actor):
    if os.environ.get("VELARORA_CLOUD_DEMO") == "true":
        raise ValueError("Training is disabled on the free cloud demo. Train locally and import trusted ONNX weights.")
    with lock:
        worker = state.training_worker
        if worker and worker._thread and worker._thread.is_alive():
            raise ValueError("A training job is already running or stopping.")
        if payload.base_model not in training.BASE_MODELS:
            raise ValueError("Choose a supported base model.")
        analysis = analyse(payload.dataset_path)
        names = analysis["names"]
        yaml_path = training.prepare_splits(analysis)
        config = dict(
            yaml_path=str(yaml_path),
            nc=len(names),
            names=names,
            base_model=payload.base_model,
            epochs=payload.epochs,
            imgsz=payload.imgsz,
            batch=payload.batch,
            run_name=payload.name + "_" + uuid.uuid4().hex[:8],
        )
        if payload.source_id:
            source = db.get_model_by_id(payload.source_id)
            if not source or not Path(source.get("pt_path") or "").is_file():
                raise ValueError("Fine-tuning requires the source PT weights.")
            if source["class_names"] != names:
                new_indices = {
                    i
                    for i, name in enumerate(names)
                    if name.casefold() not in {n.casefold() for n in source["class_names"]}
                }
                if new_indices and not payload.extend_classes:
                    raise ValueError(
                        "Confirm adding new classes, or choose a dataset matching the source model."
                    )
                if new_indices and not training._yaml_for_base(source.get("base_model") or ""):
                    raise ValueError(
                        "This imported architecture does not support adding classes. Train a new model instead."
                    )
                yaml_path, names = training.remap_dataset_for_finetune(
                    analyse(analysis["dataset_dir"]), source["class_names"], new_indices
                )
                config.update(yaml_path=str(Path(yaml_path).resolve()), nc=len(names), names=names)
            config.update(
                source_pt_path=source["pt_path"],
                source_model_id=source["id"],
                source_model_nc=source["nc"],
                source_base_model=source["base_model"],
                learning_rate=payload.learning_rate,
                freeze_backbone=payload.freeze_backbone,
            )
        state.training_worker = training.TrainingWorker()
        state.training_worker.start(config)
        db.log_action("model.train", user_id=actor["id"], detail=config["run_name"])
    return {"ok": True}


@router.post("/training")
async def train(payload: Train, actor: W):
    return await perform(begin, payload, actor)


@router.post("/training/cancel")
async def cancel(actor: W):
    if state.training_worker:
        state.training_worker.cancel()
    return {"ok": True}


def import_model(path, actor):
    from backend.core.yolo import read_model_class_names

    source = Path(path).resolve()
    if not source.is_file() or source.suffix.lower() not in (".onnx", ".pt"):
        raise ValueError("Select a trusted ONNX or PT model file.")
    if source.suffix.lower() == ".pt":
        if os.environ.get("VELARORA_CLOUD_DEMO") == "true":
            raise ValueError("The free cloud demo supports ONNX weights only. Export PT weights locally first.")
        from ultralytics import YOLO

        exported = YOLO(str(source)).export(format="onnx", imgsz=640, dynamic=True)
        onnx = str(Path(exported).resolve())
        pt = str(source)
    else:
        onnx = str(source)
        pt = None
    names = read_model_class_names(onnx)
    if not names:
        raise ValueError("This model has no class-name metadata. Export it with class names first.")
    if isinstance(names, dict):
        names = [names[k] for k in sorted(names)]
    mid = db.create_ml_model(
        source.stem, len(names), list(names), pt_path=pt, onnx_path=onnx, base_model="imported"
    )
    db.sync_classes_from_model(mid)
    db.log_action("model.import", user_id=actor["id"], entity="ml_model", entity_id=mid)
    return {"id": mid}


@router.post("/models/import-path")
async def import_path(payload: ServerPath, actor: W):
    return await perform(import_model, payload.path, actor)


@router.post("/models/upload")
async def upload_model(actor: W, file: Annotated[UploadFile, File()]):
    suffix = Path(file.filename or "").suffix.lower()
    if os.environ.get("VELARORA_CLOUD_DEMO") == "true" and suffix != ".onnx":
        raise HTTPException(400, "The free cloud demo accepts trusted ONNX weights only.")
    if suffix not in (".onnx", ".pt"):
        raise HTTPException(400, "Upload ONNX or PT weights from a trusted source.")
    content = await bounded_upload(file, 256 * 1024**2)

    def save():
        folder = training.MODELS_DIR / ("import_" + uuid.uuid4().hex)
        folder.mkdir(parents=True)
        path = folder / ("model" + suffix)
        path.write_bytes(content)
        return import_model(path, actor)

    return await perform(save)
