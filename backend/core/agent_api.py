"""Workstation-only API. Bearer credentials identify one PC and cannot stop or read teacher data."""
from fastapi import APIRouter,Header,HTTPException
from pydantic import BaseModel,Field
from nicegui import run
from backend.db.agent_credentials import authenticate_agent
from backend.db.agent_heartbeat import heartbeat

router=APIRouter(prefix='/api/workstation',tags=['workstation'])


class Sample(BaseModel):
    process: str=Field(default='',max_length=124)
    alarm_active: bool | None = None


@router.post('/heartbeat')
async def receive_sample(sample:Sample,authorization:str=Header(default='')):
    token=authorization.removeprefix('Bearer ') if authorization.startswith('Bearer ') else ''
    computer_id=await run.io_bound(authenticate_agent,token)
    if computer_id is None:
        raise HTTPException(401,'Workstation credential not recognized.')
    try:
        return await run.io_bound(heartbeat,computer_id,sample.process,sample.alarm_active)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
