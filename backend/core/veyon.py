"""Public Veyon helpers; implementations are split into focused modules."""
from backend.core.veyon_server import is_port_open, launch_webapi_server
from backend.core.veyon_directory import discover_computers, list_locations
from backend.core.veyon_auth import (
    KEY_AUTH_UUID, LOGON_AUTH_UUID, authenticate, authenticate_key, authenticate_logon,
)
from backend.core.veyon_capture import grab_framebuffer, get_logged_user, decode_image

WEBAPI_BASE_TPL = "http://{host}:{port}/api/v1"

__all__ = [
    "KEY_AUTH_UUID", "LOGON_AUTH_UUID", "WEBAPI_BASE_TPL", "is_port_open",
    "launch_webapi_server", "discover_computers", "list_locations", "authenticate",
    "authenticate_key", "authenticate_logon", "grab_framebuffer", "get_logged_user",
    "decode_image",
]
