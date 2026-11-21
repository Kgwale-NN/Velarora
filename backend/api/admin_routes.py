"""React admin endpoints. All mutations require an active admin and a session CSRF token."""
import logging
import sqlite3
from typing import Annotated
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field,ConfigDict
from nicegui import run
from backend.api.admin_security import administrator,mutation,csrf_token
from backend.api import admin_service as service
from backend.core.auth import clear_session

router=APIRouter(prefix='/api/admin',tags=['admin'])


class Teacher(BaseModel):
    model_config=ConfigDict(extra='forbid')
    username:str=Field(min_length=1,max_length=100)
    email:str=Field(min_length=3,max_length=254)
    password:str=Field(min_length=12,max_length=128)


class Classroom(BaseModel):
    name:str=Field(min_length=1,max_length=100)
    description:str=Field(default='',max_length=500)


class Members(BaseModel):
    computer_ids:list[int]=Field(max_length=1000)


async def perform(function,*args):
    try:
        return await run.io_bound(function,*args)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409,'That name or email is already in use.') from exc
    except (ValueError,PermissionError) as exc:
        raise HTTPException(400,str(exc)) from exc
    except Exception as exc:
        logging.getLogger(__name__).exception('Admin operation failed')
        raise HTTPException(500,'The change could not be completed. Please try again.') from exc


@router.get('/session')
def session(actor:Annotated[dict,Depends(administrator)]):
    return {'user':{k:actor[k] for k in ('id','username','email','role')},'csrf':csrf_token()}


@router.post('/logout')
def logout(actor:Annotated[dict,Depends(mutation)]):
    clear_session()
    return {'ok':True}


@router.get('/users')
async def users(actor:Annotated[dict,Depends(administrator)]):
    return await perform(service.users)


@router.post('/users',status_code=201)
async def create_user(payload:Teacher,actor:Annotated[dict,Depends(mutation)]):
    return await perform(service.create_teacher,actor,payload)


@router.delete('/users/{uid}')
async def remove_user(uid:int,actor:Annotated[dict,Depends(mutation)]):
    return await perform(service.delete_user,actor,uid)


@router.get('/classrooms')
async def classrooms(actor:Annotated[dict,Depends(administrator)]):
    return await perform(service.classroom_data)


@router.post('/classrooms',status_code=201)
async def create_classroom(payload:Classroom,actor:Annotated[dict,Depends(mutation)]):
    return await perform(service.save_classroom,actor,payload)


@router.put('/classrooms/{gid}')
async def edit_classroom(gid:int,payload:Classroom,actor:Annotated[dict,Depends(mutation)]):
    return await perform(service.save_classroom,actor,payload,gid)


@router.delete('/classrooms/{gid}')
async def remove_classroom(gid:int,actor:Annotated[dict,Depends(mutation)]):
    return await perform(service.delete_classroom,actor,gid)


@router.get('/classrooms/{gid}/members')
async def members(gid:int,actor:Annotated[dict,Depends(administrator)]):
    return await perform(service.members,gid)


@router.put('/classrooms/{gid}/members')
async def assign(gid:int,payload:Members,actor:Annotated[dict,Depends(mutation)]):
    return await perform(service.save_members,actor,gid,payload.computer_ids)


@router.post('/classrooms/import')
async def import_rooms(actor:Annotated[dict,Depends(mutation)]):
    from backend.config import get_settings
    from backend.services.classroom_import import import_locations
    cfg=await run.io_bound(get_settings)
    groups,computers=await perform(import_locations,cfg.get('veyon_cli',''),actor['id'])
    return {'classrooms':groups,'computers':computers}
