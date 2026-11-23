"""Workstation-only API. Bearer credentials identify one PC and cannot stop or read teacher data."""
from fastapi import APIRouter,Header,HTTPException,Request
from urllib.parse import unquote
from pydantic import BaseModel,Field
from typing import Annotated
from nicegui import run
from backend.db.agent_credentials import authenticate_agent
from backend.db.agent_heartbeat import heartbeat

router=APIRouter(prefix='/api/workstation',tags=['workstation'])
Coordinate=Annotated[float,Field(ge=0,le=1,allow_inf_nan=False)]


class Sample(BaseModel):
    process: str=Field(default='',max_length=124)
    alarm_active: bool | None = None
    capture_capable: bool = False
    native_apps: dict[str,bool] | None = Field(default=None,max_length=8)
    native_windows: list[tuple[Coordinate,Coordinate,Coordinate,Coordinate]] | None = Field(default=None,max_length=16)


@router.post('/heartbeat')
async def receive_sample(sample:Sample,authorization:str=Header(default='')):
    token=authorization.removeprefix('Bearer ') if authorization.startswith('Bearer ') else ''
    computer_id=await run.io_bound(authenticate_agent,token)
    if computer_id is None:
        raise HTTPException(401,'Workstation credential not recognized.')
    try:
        from backend.core.app_presence import record
        result = await run.io_bound(heartbeat,computer_id,sample.process,sample.alarm_active)
        record(computer_id,sample.native_apps,sample.process,sample.native_windows)
        from backend.db.agent_capture import assignment
        assigned = await run.io_bound(assignment, computer_id) if sample.capture_capable else None
        return {**result, 'capture_allowed': assigned is not None, 'capture_run_id': assigned}
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc


@router.post('/frame')
async def receive_frame(request: Request, authorization: str = Header(default=''),
                        x_velarora_run: int = Header(), x_velarora_process: str = Header(default=''),
                        x_velarora_user: str = Header(default='')):
    token = authorization.removeprefix('Bearer ') if authorization.startswith('Bearer ') else ''
    computer_id = await run.io_bound(authenticate_agent, token)
    if computer_id is None:
        raise HTTPException(401, 'Workstation credential not recognized.')
    from backend.db.agent_capture import assignment
    if await run.io_bound(assignment, computer_id) != x_velarora_run:
        raise HTTPException(409, 'This PC has no matching active screen-capture exam.')
    content = bytearray()
    async for part in request.stream():
        if len(content) + len(part) > 700000:
            raise HTTPException(413, 'Screenshot exceeds the 700 KB limit.')
        content.extend(part)
    from backend.services.agent_capture import accept
    try:
        return await run.io_bound(accept, computer_id, x_velarora_run, bytes(content),
                                  unquote(x_velarora_process), unquote(x_velarora_user))
    except PermissionError as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
