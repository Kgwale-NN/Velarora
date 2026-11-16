"""Read the foreground process on the Windows PC running Velarora."""
import ctypes
import sys
from ctypes import wintypes

import psutil


def local_windows_target(host: str) -> bool:
    return sys.platform == "win32" and host.lower() in {"localhost", "127.0.0.1", "::1"}


def foreground_app() -> str | None:
    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = wintypes.HWND
    window = user32.GetForegroundWindow()
    if not window:
        return None
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(wintypes.HWND(window), ctypes.byref(pid))
    if not pid.value:
        return None
    try:
        return psutil.Process(pid.value).name()
    except (psutil.Error, OSError):
        return None
