"""Teacher-only screen sharing; browser permission is requested by the client."""
from typing import Annotated
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from backend.api.staff_security import write_teacher
from backend.api.admin_routes import perform
from backend.config import get_settings
from backend.services import browser_monitor

router = APIRouter(prefix='/api/teacher/browser')
W = Annotated[dict, Depends(write_teacher)]


class Frame(BaseModel):
    jpeg: str = Field(min_length=10, max_length=700000)


@router.post('/start')
async def start(actor: W):
    return await perform(browser_monitor.start, actor['id'])


@router.post('/{sid}/frame')
async def frame(sid: str, payload: Frame, actor: W):
    settings = get_settings()
    return await perform(browser_monitor.frame, sid, actor['id'], payload.jpeg, settings)


@router.post('/{sid}/stop-alarm')
async def silence(sid: str, actor: W):
    return await perform(browser_monitor.stop, sid, actor['id'], True)


@router.post('/{sid}/stop')
async def stop(sid: str, actor: W):
    return await perform(browser_monitor.stop, sid, actor['id'])
