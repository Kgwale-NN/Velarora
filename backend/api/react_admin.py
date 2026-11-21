"""Serve the built React admin alongside the working NiceGUI pages."""
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse,HTMLResponse

DIST=Path(__file__).resolve().parents[2]/'frontend'/'react'/'dist'
router=APIRouter()


def register(app):
    from backend.api.admin_routes import router as api
    app.include_router(api)
    if (DIST/'assets').is_dir():
        app.add_static_files('/admin/assets',str(DIST/'assets'))
    app.include_router(router)


@router.get('/admin/{path:path}',include_in_schema=False)
def react_admin(path:str=''):
    if not (DIST/'index.html').is_file():
        return HTMLResponse('React build missing. Run npm install and npm run build in frontend/react, then restart Velarora.',status_code=503)
    return FileResponse(DIST/'index.html',headers={'Cache-Control':'no-store'})


def redirect_if_built(path):
    if not (DIST/'index.html').is_file():
        return False
    from nicegui import ui
    ui.navigate.to('/admin/'+path)
    return True
