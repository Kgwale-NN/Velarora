"""Capture the Windows virtual desktop, including both screens on dual-monitor PCs."""
from io import BytesIO
from PIL import Image, ImageGrab


def capture():
    image=ImageGrab.grab(all_screens=True,include_layered_windows=True).convert('RGB')
    image.thumbnail((1920,1080),Image.Resampling.LANCZOS)
    for quality in (75,55,40):
        output=BytesIO()
        image.save(output,format='JPEG',quality=quality)
        if output.tell()<=650000:
            return output.getvalue()
        image.thumbnail((1280,720),Image.Resampling.LANCZOS)
    raise ValueError('Screenshot exceeds the upload limit.')
