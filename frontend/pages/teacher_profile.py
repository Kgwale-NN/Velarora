"""Teacher self-service profile, separate from the administrator's /profile page."""
import logging
from nicegui import app, run, ui
from backend.core.auth import require_auth, clear_session
from backend.db.user_queries import get_user_by_id
from backend.db.teacher_profile import update_teacher_name
from frontend.pages._nav import nav, password_dialog
from frontend.pages.admin_shell import toast
from frontend.pages.design_assets import stylesheet
from frontend.pages.glass_fields import text_field


@ui.page('/teacher-profile')
async def teacher_profile():
    current = require_auth('teacher')
    if current is None:
        return
    user = await run.io_bound(get_user_by_id,current['id'])
    if not user or not user['is_active'] or user['role'] != 'teacher':
        clear_session()
        ui.navigate.to('/login')
        return
    nav(current)
    stylesheet('teacher-profile.css')
    password = password_dialog(current)
    with ui.column().classes('teacher-profile-page w-full'):
        with ui.column().classes('teacher-profile-heading'):
            ui.label('My Profile').classes('teacher-profile-title')
            ui.label('Manage your display name and password.').classes('teacher-profile-subtitle')
        with ui.element('div').classes('teacher-profile-grid w-full'):
            with ui.card().classes('teacher-profile-details'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('person_outline').classes('profile-section-icon')
                    ui.label('Account details').classes('profile-section-title')
                name = text_field('Display name',icon='person_outline',value=user['username'],placeholder='Enter your display name')
                text_field('Email address',icon='mail_outline',value=user['email'] or '',props='readonly type=email')
                ui.label('Use this email address to sign in.').classes('profile-help')
                text_field('Role',icon='badge',value='Teacher',props='readonly')
                error = ui.label('').classes('account-form-error').props('role=alert')
                save_button = ui.button('Save profile',icon='check').props('no-caps')
            with ui.card().classes('teacher-profile-security'):
                ui.icon('lock_outline').classes('profile-section-icon')
                ui.label('Password').classes('profile-section-title')
                ui.label('Enter your current password before choosing a new one.').classes('profile-help')
                ui.button('Change password',icon='lock_outline',on_click=password.open).props('outline no-caps')

    async def save():
        if save_button.props.get('loading'):
            return
        value = name.value or ''
        error.set_text('')
        save_button.props('loading')
        name.props('disable')
        try:
            saved = await run.io_bound(update_teacher_name,current['id'],value)
        except ValueError as exc:
            error.set_text(str(exc))
            return
        except Exception:
            logging.getLogger(__name__).exception('Teacher profile save failed')
            error.set_text('Your profile could not be saved. Please try again.')
            return
        finally:
            save_button.props(remove='loading')
            name.props(remove='disable')
        name.set_value(saved)
        app.storage.user['auth'] = {**current,'username':saved}
        toast('Profile saved.',type='positive')
    save_button.on_click(save)
