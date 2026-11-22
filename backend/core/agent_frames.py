"""Bounded latest-frame mailbox for outbound agents; no browser or agent can read it."""
from dataclasses import dataclass
import threading
import time


@dataclass(frozen=True)
class Frame:
    raw: bytes
    process: str
    username: str
    received: float
    sequence: int


_lock = threading.Lock()
_frames = {}
_sequence = 0
MAX_BYTES = 32 * 1024 * 1024
TTL = 12


def put(computer_id, run_id, raw, process, username):
    global _sequence
    now = time.perf_counter()
    with _lock:
        for key in list(_frames):
            if now - _frames[key].received > TTL or key[0] == computer_id:
                del _frames[key]
        while _frames and sum(len(frame.raw) for frame in _frames.values()) + len(raw) > MAX_BYTES:
            del _frames[min(_frames, key=lambda key: _frames[key].received)]
        _sequence += 1
        _frames[(computer_id, run_id)] = Frame(raw, process, username, now, _sequence)


def latest(computer_id, run_id, after=0):
    with _lock:
        frame = _frames.get((computer_id, run_id))
        if frame and frame.sequence > after and time.perf_counter() - frame.received <= TTL:
            return frame
    return None


def clear_run(run_id):
    with _lock:
        for key in list(_frames):
            if key[1] == run_id:
                del _frames[key]
