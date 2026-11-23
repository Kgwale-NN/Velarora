"""Validate agent screenshots before placing them in a run-bound mailbox."""
import io
from PIL import Image, UnidentifiedImageError
from backend.db.agent_capture import assignment
from backend.db.application_policy import normalize_process
from backend.core import agent_frames


def accept(computer_id, run_id, content, process='', username=''):
    if assignment(computer_id) != run_id:
        raise PermissionError('This PC has no matching active screen-capture exam.')
    if not content or len(content) > 700000:
        raise ValueError('Send a JPEG screenshot of at most 700 KB.')
    if len(process) > 124 or len(username) > 124 or any(ord(c) < 32 for c in username):
        raise ValueError('Invalid workstation identity fields.')
    process = normalize_process(process) if process else ''
    try:
        # Reject other formats before Pillow/Ultralytics can attempt to install
        # an optional decoder for an invalid or unrelated upload.
        if not content.startswith(b'\xff\xd8\xff'):
            raise ValueError('Screenshot must be a JPEG.')
        with Image.open(io.BytesIO(content), formats=['JPEG']) as image:
            if image.format != 'JPEG' or not (1 <= image.width <= 1920 and 1 <= image.height <= 1080):
                raise ValueError('Screenshot must be a JPEG no larger than 1920 by 1080.')
            image.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError('Screenshot could not be decoded.') from exc
    # An exam might have ended during upload/verification. Never publish to the next run.
    if assignment(computer_id) != run_id:
        raise PermissionError('The screen-capture exam ended during upload.')
    agent_frames.put(computer_id, run_id, content, process, username)
    return {'accepted': True}
