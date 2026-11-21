"""Real ONNX execution, letterbox coordinates, class scores and NMS."""
import base64
import io
import numpy as np
import pytest
from PIL import Image
from backend.core.browser_boxes import decode
from backend.core import browser_inference as vision


def test_onnx_execution_and_wide_screen_coordinates(tmp_path, monkeypatch):
    import onnx
    from onnx import helper, numpy_helper, TensorProto
    values = np.array([[[320], [320], [320], [180], [.95]]], dtype=np.float32)
    graph = helper.make_graph(
        [helper.make_node('Constant', [], ['output'], value=numpy_helper.from_array(values))],
        'test-detector', [helper.make_tensor_value_info('images', TensorProto.FLOAT, [1, 3, 640, 640])],
        [helper.make_tensor_value_info('output', TensorProto.FLOAT, [1, 5, 1])],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid('', 17)])
    model.ir_version = 9
    path = tmp_path / 'test.onnx'
    onnx.save(model, path)
    monkeypatch.setattr(vision, '_session', None)
    monkeypatch.setattr(vision, '_path', None)
    result = vision.predict(Image.new('RGB', (1280, 720)),
        {'onnx_path': str(path), 'imgsz': 640, 'class_names': ['Notepad']})
    assert result[0]['name'] == 'Notepad'
    assert result[0]['box'] == [320, 180, 960, 540]
    assert result[0]['conf'] == pytest.approx(.95)


def test_classic_objectness_and_class_aware_suppression():
    output = np.array([[[100, 100, 40, 40, .9, .9, .1],
                        [100, 100, 40, 40, .8, .9, .1],
                        [100, 100, 40, 40, .9, .1, .9],
                        [200, 200, 40, 40, .1, .99, .01]]])
    rows = decode(output, ['Notepad', 'Other'], (640, 640, 0, 0, 640, 640), .5, .4)
    assert len(rows) == 2
    assert {r['name'] for r in rows} == {'Notepad', 'Other'}
    assert all(r['conf'] == pytest.approx(.81) for r in rows)


def test_invalid_oversized_or_non_jpeg_capture_is_rejected():
    with pytest.raises(ValueError):
        vision.open_frame('not base64')
    for image, format_ in [(Image.new('RGB', (10, 10)), 'PNG'),
                           (Image.new('RGB', (2000, 2000)), 'JPEG')]:
        buffer = io.BytesIO()
        image.save(buffer, format_)
        with pytest.raises(ValueError):
            vision.open_frame(base64.b64encode(buffer.getvalue()).decode())


def test_empty_detections_and_unsupported_output():
    output = np.zeros((1, 5, 20), dtype=np.float32)
    assert decode(output, ['Notepad'], (640, 640, 0, 0, 640, 640)) == []
    with pytest.raises(ValueError):
        decode(np.zeros((1, 3, 19)), ['Notepad'], (640, 640, 0, 0, 640, 640))
