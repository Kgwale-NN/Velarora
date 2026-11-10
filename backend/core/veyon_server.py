"""Check the Veyon port and start its WebAPI service."""
import os
import socket
import subprocess
from typing import Optional


def is_port_open(host: str, port: int, timeout: float = 1.5) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex((host, port)) == 0


def launch_webapi_server(veyon_cli: str) -> Optional[subprocess.Popen]:
    kwargs: dict = {}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        return subprocess.Popen([veyon_cli, "webapi", "runserver"], **kwargs)
    except Exception:
        return None
