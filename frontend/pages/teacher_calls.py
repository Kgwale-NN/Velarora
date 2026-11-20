"""Worker calls remain bound to the signed-in teacher, including after shared-screen logout."""
from nicegui import app
from backend.db.teacher_scope import bind as database_bind


def bind(user_id,function):
    return database_bind(user_id,function,session=app.storage.user)
