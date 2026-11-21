"""Decode standard YOLOv5/v8 ONNX outputs and suppress overlapping class boxes."""
import numpy as np


def decode(output, names, transform, confidence=.5, overlap=.45):
    raw = np.asarray(output)
    if raw.ndim != 3 or raw.shape[0] != 1:
        raise ValueError("Use a standard batch-one YOLO detection ONNX export without embedded NMS.")
    rows = raw[0]
    nc = len(names)
    if rows.shape[0] in (nc + 4, nc + 5):
        rows = rows.T
    if rows.shape[1] not in (nc + 4, nc + 5):
        raise ValueError("This model output format is not supported by browser monitoring.")
    scores = rows[:, -nc:]
    if rows.shape[1] == nc + 5:
        scores = scores * rows[:, 4:5]
    classes = scores.argmax(axis=1)
    best = scores.max(axis=1)
    keep = np.isfinite(rows).all(axis=1) & (best >= confidence)
    rows, classes, best = rows[keep], classes[keep], best[keep]
    order = best.argsort()[::-1][:1000]
    rows, classes, best = rows[order], classes[order], best[order]
    boxes = np.column_stack((rows[:, :2] - rows[:, 2:4] / 2,
                             rows[:, :2] + rows[:, 2:4] / 2))
    chosen = []
    order = np.arange(len(boxes))
    while len(order) and len(chosen) < 40:
        i = order[0]
        chosen.append(i)
        rest = order[1:]
        a = np.maximum(boxes[i, :2], boxes[rest, :2])
        b = np.minimum(boxes[i, 2:], boxes[rest, 2:])
        intersection = np.maximum(b - a, 0).prod(axis=1)
        area = np.maximum(boxes[:, 2:] - boxes[:, :2], 0).prod(axis=1)
        iou = intersection / np.maximum(area[i] + area[rest] - intersection, 1e-6)
        order = rest[(classes[rest] != classes[i]) | (iou <= overlap)]
    width, height, pad_x, pad_y, resized_w, resized_h = transform
    result = []
    for i in chosen:
        box = boxes[i].copy()
        box[[0, 2]] = np.clip((box[[0, 2]] - pad_x) * width / resized_w, 0, width)
        box[[1, 3]] = np.clip((box[[1, 3]] - pad_y) * height / resized_h, 0, height)
        if box[2] > box[0] and box[3] > box[1]:
            cls = int(classes[i])
            result.append({"class_id": cls, "name": names[cls], "conf": float(best[i]),
                           "box": [int(round(v)) for v in box]})
    return result
