"""Admin JSON API uses the existing browser session, live roles, and CSRF protection."""
import secrets
import threading

_CSRF_LOCK=threading.Lock()
from typing import Annotated
from fastapi import HTTPException,Header,Depends,Response
from nicegui import app
from backend.core.auth import get_session_user
from backend.db.user_queries import get_user_by_id


def browser_state():
    return app.storage.user


def administrator(response:Response):
    response.headers['Cache-Control']='no-store'
    session=get_session_user()
    if not session:
        raise HTTPException(401,'Sign in to continue.')
    user=get_user_by_id(session['id'])
    if not user or not user['is_active'] or user['role']!='admin':
        raise HTTPException(403,'Administrator access is required.')
    return user


def csrf_token():
    with _CSRF_LOCK:
        state=browser_state()
        if not state.get('admin_csrf'):
            state['admin_csrf']=secrets.token_urlsafe(32)
        return state['admin_csrf']


def mutation(actor:Annotated[dict,Depends(administrator)],x_csrf_token:str=Header(default='')):
    expected=browser_state().get('admin_csrf','')
    if not expected or not secrets.compare_digest(expected,x_csrf_token):
        raise HTTPException(403,'Refresh the page before making changes.')
    return actor
