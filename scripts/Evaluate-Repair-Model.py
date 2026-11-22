"""Check a Notepad candidate on reviewed screenshots at the browser capture size."""
import argparse
import io
import json
from pathlib import Path
import sys
from PIL import Image


def iou(first, second):
    x1, y1 = max(first[0], second[0]), max(first[1], second[1])
    x2, y2 = min(first[2], second[2]), min(first[3], second[3])
    intersection = max(0, x2-x1) * max(0, y2-y1)
    area = lambda b: max(0, b[2]-b[0]) * max(0, b[3]-b[1])
    return intersection / max(1, area(first) + area(second) - intersection)


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from backend.core.browser_inference import predict
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--split', choices=['val', 'test'], required=True)
    parser.add_argument('--confidence', type=float, default=.4)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    model = {'onnx_path': str(args.model.resolve()), 'imgsz': 640, 'class_names': ['Notepad']}
    results = []
    for path in sorted((args.data / 'images' / args.split).glob('*.jpg')):
        image = Image.open(path).convert('RGB')
        image.thumbnail((1280, 720), Image.Resampling.BILINEAR)
        capture = io.BytesIO()
        image.save(capture, 'JPEG', quality=72)
        image = Image.open(io.BytesIO(capture.getvalue())).convert('RGB')
        width, height = image.size
        label = (args.data / 'labels' / args.split / (path.stem + '.txt')).read_text().strip()
        expected = []
        for line in label.splitlines():
            cls, cx, cy, w, h = map(float, line.split())
            if cls != 0:
                raise ValueError('This repair check expects the single Notepad class.')
            expected.append([(cx-w/2)*width, (cy-h/2)*height,
                             (cx+w/2)*width, (cy+h/2)*height])
        detections = predict(image, model, args.confidence, .2)
        # Browser mode keeps only the highest scoring box for a class by default.
        best = max(detections, key=lambda d: d['conf']) if detections else None
        correct = (best is None) if not expected else bool(
            best and any(iou(best['box'], box) >= .5 for box in expected))
        results.append({'image': path.name, 'target_present': bool(expected), 'correct': correct,
                        'best_prediction': best})
    positive = [r for r in results if r['target_present']]
    negative = [r for r in results if not r['target_present']]
    report = {'split': args.split, 'confidence': args.confidence, 'positive_screens': len(positive),
              'correct_positive_screens': sum(r['correct'] for r in positive),
              'negative_screens': len(negative), 'false_alarm_screens': sum(not r['correct'] for r in negative),
              'results': results, 'note': 'Small, same-PC screenshot check; not a guarantee on unseen PCs.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != 'results'}, indent=2))


if __name__ == '__main__':
    main()
