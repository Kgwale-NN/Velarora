"""Read computers and rooms from Veyon's built-in directory."""
import json
import subprocess
from backend.core.veyon_locations import group_locations


def discover_computers(veyon_cli: str) -> list[dict]:
    """Return list of {"name": str, "host": str} from Veyon's built-in directory."""
    r = subprocess.run(
        [veyon_cli, "config", "get", "BuiltinDirectory/NetworkObjects"],
        capture_output=True, text=True, timeout=10,
    )
    raw = r.stdout.strip()
    if not raw:
        raise RuntimeError(r.stderr.strip() or "veyon-cli returned nothing")
    if "=" in raw:
        raw = raw.split("=", 1)[1].strip()
    return [
        {"name": o["Name"], "host": o["HostAddress"]}
        for o in json.loads(raw)
        if o.get("Type") == 3 and o.get("HostAddress")
    ]


def list_locations(veyon_cli: str) -> list[dict]:
    """
    Parse Veyon's BuiltinDirectory/NetworkObjects and return locations with their
    computers.  Veyon object types: 1 = location/room, 3 = computer.
    Returns: [{"name": str, "computers": [{"name": str, "host": str}]}]
    Only locations that contain at least one computer are returned.

    Three strategies are tried in order so this works across Veyon versions:
      1. UID-based:       each computer carries a ParentUid pointing to a location Uid
      2. Sequential:      location object immediately precedes its computers in the list
      3. Flat fallback:   no location objects at all — all computers go into one group
    """
    r = subprocess.run(
        [veyon_cli, "config", "get", "BuiltinDirectory/NetworkObjects"],
        capture_output=True, text=True, timeout=10,
    )
    raw = r.stdout.strip()
    if not raw:
        return []
    if "=" in raw:
        raw = raw.split("=", 1)[1].strip()
    try:
        objects = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(objects, list):
        objects = []
    return group_locations(objects)
