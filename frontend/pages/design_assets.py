"""Versioned browser-cacheable assets shared by login and admin pages."""
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from nicegui import app, ui

ASSETS = Path(__file__).parents[1] / "assets"
app.add_static_files("/design-assets", str(ASSETS))


@lru_cache(maxsize=32)
def asset_url(name: str) -> str:
    version = sha256((ASSETS / name).read_bytes()).hexdigest()[:12]
    return f"/design-assets/{name}?v={version}"


def stylesheet(name: str) -> None:
    ui.add_head_html(f'<link rel="stylesheet" href="{asset_url(name)}">')
