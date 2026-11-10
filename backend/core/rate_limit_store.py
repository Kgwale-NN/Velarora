"""Thread-safe sliding-window counters, shared by all login attempts.

Expired entries are swept when the store reaches 4096 keys. State is local
 to this process and is cleared when the server restarts.
"""
import threading
import time
from backend.config import LOGIN_MAX_ATTEMPTS, LOGIN_WINDOW_SEC

MAX_ATTEMPTS = LOGIN_MAX_ATTEMPTS
WINDOW_SEC = float(LOGIN_WINDOW_SEC)
_MAX_KEYS = 4096
_lock = threading.Lock()
_failures: dict[str, list[float]] = {}


def _prune(times: list[float], now: float) -> list[float]:
    cutoff = now - WINDOW_SEC
    return [t for t in times if t > cutoff]


def is_blocked(key: str) -> bool:
    """True if `key` has exhausted its attempts and must wait."""
    return retry_after(key) > 0


def retry_after(key: str) -> float:
    """
    Seconds until `key` may try again, or 0 if it is not blocked.
    Also prunes expired entries as a side effect.
    """
    now = time.monotonic()
    with _lock:
        times = _prune(_failures.get(key, []), now)
        if times:
            _failures[key] = times
        else:
            _failures.pop(key, None)
        if len(times) < MAX_ATTEMPTS:
            return 0.0
        # Blocked until the oldest failure leaves the window.
        return max(0.0, times[0] + WINDOW_SEC - now)


def record_failure(key: str) -> None:
    """Register one failed attempt for `key`."""
    now = time.monotonic()
    with _lock:
        if len(_failures) >= _MAX_KEYS:
            _sweep_expired(now)
        times = _prune(_failures.get(key, []), now)
        times.append(now)
        _failures[key] = times


def record_success(key: str) -> None:
    """Clear all failure history for `key` (called after a successful login)."""
    with _lock:
        _failures.pop(key, None)


def reset_all() -> None:
    """Clear every key — used by tests."""
    with _lock:
        _failures.clear()


def _sweep_expired(now: float) -> None:
    """Drop every fully-expired key. Caller must hold _lock."""
    for k in list(_failures):
        kept = _prune(_failures[k], now)
        if kept:
            _failures[k] = kept
        else:
            del _failures[k]
