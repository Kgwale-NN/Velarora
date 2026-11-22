"""Train a separate CPU candidate from a reviewed dataset; never activate it automatically."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--weights', type=Path, required=True)
    parser.add_argument('--epochs', type=int, default=20)
    args = parser.parse_args()
    if not args.data.is_file() or not args.weights.is_file():
        parser.error('Both the reviewed data.yaml and trusted local PT checkpoint must exist.')
    os.environ.setdefault('OMP_NUM_THREADS', '4')
    os.environ.setdefault('YOLO_OFFLINE', 'true')
    import torch
    from ultralytics import YOLO
    torch.set_num_threads(4)
    directory = Path('data/model-repair').resolve()
    directory.mkdir(parents=True, exist_ok=True)
    name = 'notepad_candidate_' + datetime.now().strftime('%Y%m%d_%H%M%S')
    status = directory / 'status.json'

    def write(**values):
        status.write_text(json.dumps(values, indent=2), encoding='utf-8')

    def progress(trainer):
        write(stage='training', epoch=trainer.epoch + 1, epochs=trainer.epochs,
              metrics={key: float(value) for key, value in trainer.metrics.items()},
              output=str(trainer.save_dir))

    model = YOLO(str(args.weights.resolve()))
    model.add_callback('on_fit_epoch_end', progress)
    write(stage='starting', epochs=args.epochs, output=str(directory / name))
    model.train(data=str(args.data.resolve()), epochs=args.epochs, batch=4, imgsz=640,
                device='cpu', workers=0, cache=False, project=str(directory), name=name,
                exist_ok=False, plots=False, verbose=False, seed=42, patience=6,
                optimizer='AdamW', lr0=.0005, lrf=.1, fliplr=0, mosaic=0,
                close_mosaic=0, hsv_h=0, hsv_s=.1, hsv_v=.15,
                translate=.08, scale=.15, amp=False)
    checkpoint = Path(model.trainer.save_dir) / 'weights/best.pt'
    write(stage='exporting', checkpoint=str(checkpoint))
    exported = YOLO(str(checkpoint)).export(format='onnx', imgsz=640, dynamic=True,
                                           batch=1, simplify=False, opset=17, device='cpu')
    write(stage='needs-independent-evaluation', checkpoint=str(checkpoint), onnx=str(exported),
          note='Candidate only. Current desktop and hosted models have not been changed.')
    print('Candidate exported. Evaluate held-out open and closed screens before activation.')


if __name__ == '__main__':
    main()
