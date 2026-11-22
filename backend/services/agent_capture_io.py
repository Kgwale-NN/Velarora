"""Feed authenticated outbound screenshots into the existing local AI pipeline."""
import queue
from backend.core import agent_frames
from backend.core.veyon_capture import decode_image
from backend.db.database import auto_create_student, get_user_by_id, get_user_by_username


def run(controller, name):
    computer_id = controller.state.computer_ids[name]
    sequence = 0
    last_username = None
    controller._log(f'[{name}] Waiting for this PC’s outbound screen agent')
    while not controller._stop.is_set():
        frame = agent_frames.latest(computer_id, controller.run_id, sequence)
        if frame is None:
            controller._stop.wait(.25)
            continue
        sequence = frame.sequence
        image = decode_image(frame.raw)
        if image is None:
            continue
        username = frame.username.split('\\')[-1].strip()
        if username != last_username:
            user = get_user_by_username(username) if username else None
            if username and user is None:
                user = get_user_by_id(auto_create_student(username))
            controller.state.computer_users[name] = user['id'] if user else None
            controller.state.computer_os_usernames[name] = username or None
            last_username = username
        try:
            controller._raw_q.put((name, frame.raw, image, frame.received, frame.process or None), timeout=.5)
        except queue.Full:
            pass
        controller._stop.wait(max(.1, float(controller.cfg['interval'])))
