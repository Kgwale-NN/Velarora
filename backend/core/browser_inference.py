"""Small CPU-only ONNX inference path; caller serializes model and frame work."""
import base64
import binascii
import gc
import io
from pathlib import Path
import numpy as np
from PIL import Image, UnidentifiedImageError
from backend.core.browser_boxes import decode

_session = None
_path = None


def open_frame(encoded):
    try:
        if len(encoded) > 700000:
            raise ValueError("Screen capture is too large.")
        content = base64.b64decode(encoded, validate=True)
        image = Image.open(io.BytesIO(content))
        if image.format != "JPEG" or image.width * image.height > 1920 * 1080:
            raise ValueError("Share a JPEG frame no larger than 1920 × 1080.")
        image.load()
        image = image.convert("RGB")
        # Store a clean JPEG, never arbitrary browser-supplied file bytes.
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", quality=75)
        return image, buffer.getvalue()
    except (binascii.Error, UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("Screen capture could not be read. Share your screen again.") from exc


def model_session(model):
    global _session, _path
    path = model.get("onnx_path")
    if not path or not Path(path).is_file():
        raise ValueError("Ask your administrator to upload and activate the trained ONNX model.")
    resolved = str(Path(path).resolve())
    if _session is None or _path != resolved:
        import onnxruntime as ort
        _session, _path = None, None
        gc.collect()
        options = ort.SessionOptions()
        options.intra_op_num_threads = options.inter_op_num_threads = 1
        options.enable_cpu_mem_arena = False
        options.enable_mem_pattern = False
        _session = ort.InferenceSession(resolved, options, providers=["CPUExecutionProvider"])
        _path = resolved
    return _session


def predict(image, model, confidence=.5, overlap=.45):
    session = model_session(model)
    input_ = session.get_inputs()[0]
    shape = input_.shape
    if len(shape) != 4 or shape[1] != 3 or input_.type != "tensor(float)":
        raise ValueError("Use a standard float32 RGB YOLO ONNX model.")
    width, height = image.size
    size = int(model.get("imgsz") or 640)
    target_h = shape[2] if isinstance(shape[2], int) else size
    target_w = shape[3] if isinstance(shape[3], int) else size
    if not (128 <= target_h <= 640 and 128 <= target_w <= 640):
        raise ValueError("For the free demo, export the model at 640 pixels or smaller.")
    ratio = min(target_w / width, target_h / height)
    resized = image.resize((max(1, round(width * ratio)), max(1, round(height * ratio))), Image.Resampling.BILINEAR)
    pad_x, pad_y = (target_w - resized.width) // 2, (target_h - resized.height) // 2
    canvas = Image.new("RGB", (target_w, target_h), (114, 114, 114))
    canvas.paste(resized, (pad_x, pad_y))
    tensor = np.asarray(canvas, dtype=np.float32).transpose(2, 0, 1)[None] / 255
    output = session.run(None, {input_.name: tensor})[0]
    transform = (width, height, pad_x, pad_y, resized.width, resized.height)
    return decode(output, model["class_names"], transform, confidence, overlap)
