"""Safe API projections and existing domain operations; credentials never leave the server."""
from backend.db import database as db
from backend.db._core import _conn
from backend.db.staff_email import normalize_email
from backend.db.group_membership import set_group_computers


def users():
    return [{k:u[k] for k in ('id','username','email','role','is_active','created_at')} for u in db.list_users()]


def create_teacher(actor,payload):
    name=payload.username.strip()
    if not name or len(name)>100:
        raise ValueError('Enter a name between 1 and 100 characters.')
    email=normalize_email(payload.email)
    with _conn():
        uid=db.create_user(name,payload.password,'teacher',created_by_id=actor['id'],email=email)
    db.log_action('user.create_admin_api',user_id=actor['id'],entity='user',entity_id=uid)
    return {'id':uid}


def delete_user(actor,uid):
    target=db.get_user_by_id(uid)
    if not target:
        raise ValueError('This user no longer exists.')
    if target['role']=='admin' or uid==actor['id']:
        raise ValueError('Administrator accounts cannot be deleted here.')
    db.delete_user(uid)
    db.log_action('user.delete_admin_api',user_id=actor['id'],entity='user',entity_id=uid)
    return {'ok':True}


def classroom_data():
    return {'classrooms':db.list_groups(),'computers':db.list_computers()}


def save_classroom(actor,payload,gid=None):
    name=payload.name.strip()
    if not name or len(name)>100:
        raise ValueError('Enter a classroom name between 1 and 100 characters.')
    if gid is None:
        gid=db.create_group(name,payload.description.strip())
    else:
        db.update_group(gid,name,payload.description.strip())
    db.log_action('classroom.save',user_id=actor['id'],entity='computer_group',entity_id=gid)
    return {'id':gid}


def members(gid):
    if not db.get_group(gid):
        raise ValueError('This classroom no longer exists.')
    return [c['id'] for c in db.list_computers_in_group(gid)]


def save_members(actor,gid,ids):
    set_group_computers(gid,ids,user_id=actor['id'])
    return {'ok':True}


def delete_classroom(actor,gid):
    if not db.get_group(gid):
        raise ValueError('This classroom no longer exists.')
    db.delete_group(gid)
    db.log_action('classroom.delete',user_id=actor['id'],entity='computer_group',entity_id=gid)
    return {'ok':True}
