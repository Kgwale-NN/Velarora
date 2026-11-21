"""Draw saved detection boxes on cloud screenshots without loading OpenCV."""
import base64
import io
from PIL import Image, ImageDraw


def annotate_jpeg(content, detections):
    image = Image.open(io.BytesIO(content)).convert('RGB')
    draw = ImageDraw.Draw(image)
    for x1, y1, x2, y2, color, name, confidence in detections:
        draw.rectangle((x1, y1, x2, y2), outline=color, width=2)
        label = f'{name} {confidence:.0%}'
        y = max(0, y1 - 16)
        bounds = draw.textbbox((x1 + 3, y), label)
        draw.rectangle(bounds, fill='#111111')
        draw.text((x1 + 3, y), label, fill='#ffffff')
    output = io.BytesIO()
    image.save(output, 'JPEG', quality=80)
    return 'data:image/jpeg;base64,' + base64.b64encode(output.getvalue()).decode()
