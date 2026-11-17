"""
frontend/pages/users.py
──────────────────
User management page  /users  (teacher + admin)

Heavy DB work (auto-assigning historical events on create, nullifying events
on delete) runs in background asyncio tasks so the UI returns immediately.
"""
import asyncio
from nicegui import ui
from nicegui import context as _ctx

from backend.core.auth import is_admin, require_auth
from backend.db.database import (
    MIN_PASSWORD_LENGTH,
    activate_user,
    auto_assign_user_events,
    create_user,
    delete_user,
    list_users,
    nullify_user_events,
)
from backend.db.staff_email import link_account_email
from frontend.pages.admin_shell import toast
from frontend.pages._nav import nav
from frontend.pages.password_field import new_password_field
from frontend.pages.glass_fields import text_field, select_field
from frontend.translate import t


@ui.page("/users")
def page_users() -> None:
    current = require_auth(required_role="teacher_or_admin")
    if current is None:
        return
    nav(current)
    admin = is_admin(current)

    with ui.column().classes("w-full p-4 gap-4"):
        with ui.row().classes("users-dashboard-heading w-full items-center justify-between"):
            ui.label("User dashboard").classes("text-2xl")
            add_user = ui.button("Add user", icon="person_add").props("no-caps").classes("users-add-button")

        totals = {}
        with ui.element("section").classes("users-stat-grid").props('aria-label="User totals"'):
            for key, title, icon in [
                ("total", "Total users", "people_outline"),
                ("active", "Active accounts", "verified_user"),
                ("teachers", "Teachers", "school"),
                ("students", "Students", "person_outline"),
            ]:
                with ui.card().classes("user-stat-card"):
                    with ui.row().classes("w-full items-center justify-between"):
                        ui.label(title).classes("user-stat-title")
                        ui.icon(icon).classes("user-stat-icon").props("aria-hidden=true")
                    totals[key] = ui.label("0").classes("user-stat-number").props(
                        f'aria-label="{title} count"')
            inactive_note = ui.label("").classes("users-count-note")

        # Account creation stays in a focused dialog above the dashboard.
        with ui.dialog() as create_dialog, ui.card().classes(
            "user-create-dialog"
        ).on("click.stop", js_handler="() => {}").on("pointerdown.stop", js_handler="() => {}"):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label("Create account").classes("text-2xl")
                cancel_create = ui.button(icon="close", on_click=create_dialog.close).props(
                    'flat round dense aria-label="Close create account"')
            with ui.element("div").classes("user-create-grid"):
                new_username = text_field(
                    t("users_username"), icon="person_outline", classes="user-name-field",
                    props='autocomplete=off', value="",
                )
                new_password = text_field(
                    t("users_temp_password"), icon="lock_outline", new_password=True,
                    classes="user-create-password",
                )
                new_email = text_field(
                    t("staff_email"), icon="mail_outline", classes="user-email-field",
                    props="type=email autocomplete=off",
                )
                if admin:
                    new_role = select_field(
                        t("users_role"), {"student": t("users_role_student"), "teacher": t("users_role_teacher")},
                        value="student", classes="user-role-field",
                    )
                    role_hint = ui.label(t("users_hint_windows")).classes(
                        "text-sm text-gray-400 user-role-hint")

                    def _update_hint() -> None:
                        role_hint.set_text(
                            t("users_hint_student") if new_role.value == "student"
                            else t("users_hint_any")
                        )
                    new_role.on_value_change(lambda _: _update_hint())

                form_msg = ui.label("").classes("text-sm user-form-message")
                create_btn = ui.button(t("users_create_btn")).props("no-caps").classes("user-create-button")

                async def do_create() -> None:
                    uname = new_username.value.strip()
                    pwd   = new_password.value
                    role  = new_role.value if admin else "student"

                    email = new_email.value.strip()
                    if not uname or not pwd or email == "":
                        form_msg.set_text(t("users_fill_fields"))
                        form_msg.classes(replace="text-sm user-form-message text-red-500")
                        return

                    # Same policy as the DB layer (validate_password) —
                    # checked here too for a friendlier inline error.
                    if len(pwd) < MIN_PASSWORD_LENGTH:
                        form_msg.set_text(
                            t("pwd_err_short").format(n=MIN_PASSWORD_LENGTH))
                        form_msg.classes(replace="text-sm user-form-message text-red-500")
                        return

                    if create_btn._props.get("loading"):
                        return
                    create_btn.props("loading")
                    cancel_create.disable()
                    create_dialog.props("persistent")
                    form_msg.set_text(t("users_creating"))
                    form_msg.classes(replace="text-sm user-form-message text-gray-500 dark:text-gray-400")

                    loop = asyncio.get_event_loop()
                    try:
                        new_uid = await loop.run_in_executor(
                            None, lambda: create_user(
                                uname, pwd, role,
                                created_by_id=current["id"], email=email,
                            )
                        )
                        # Show success immediately — event assignment runs in background
                        if role == "student":
                            form_msg.set_text(
                                t("users_created_linking").format(uname=uname))
                        else:
                            form_msg.set_text(
                                t("users_created_teacher").format(uname=uname))
                        form_msg.classes(replace="text-sm user-form-message text-green-600")
                        new_username.set_value("")
                        new_password.set_value("")
                        new_email.set_value("")
                        _refresh()
                        create_dialog.close()
                        toast("Account created.", type="positive")

                        if role == "student":
                            asyncio.create_task(
                                _assign_events_bg(new_uid, uname, form_msg, _ctx.client))

                    except Exception as e:
                        form_msg.set_text(t("users_error").format(e=e))
                        form_msg.classes(replace="text-sm user-form-message text-red-500")
                    finally:
                        create_btn.props(remove="loading")
                        cancel_create.enable()
                        create_dialog.props(remove="persistent")

                create_btn.on_click(do_create)

        def reset_create() -> None:
            new_username.set_value("")
            new_password.set_value("")
            new_email.set_value("")
            for field in (new_username, new_password, new_email):
                field.update()
            form_msg.set_text("")
            new_password.error = None
            if admin:
                new_role.set_value("student")

        def show_create() -> None:
            reset_create()
            create_dialog.open()

        add_user.on_click(show_create)
        create_dialog.on("hide", reset_create)

        if admin:
            email_target = [None]
            with ui.dialog() as email_dialog, ui.card().classes("user-email-dialog"):
                ui.label("Add sign-in email").classes("text-lg font-semibold")
                email_name = ui.label("").classes("text-sm text-gray-300")
                address = text_field(t("staff_email"), icon="mail_outline", props="type=email")
                address_error = ui.label("").classes("text-sm text-red-300")

                def assign_email() -> None:
                    if email_target[0] is None:
                        return
                    try:
                        link_account_email(email_target[0], address.value)
                    except ValueError as exc:
                        address_error.set_text(str(exc))
                        return
                    _refresh()
                    email_dialog.close()
                    toast("Sign-in email saved.", type="positive")

                with ui.row().classes("w-full justify-end gap-3"):
                    ui.button("Cancel", on_click=email_dialog.close).props("flat no-caps")
                    ui.button("Save email", on_click=assign_email).props("no-caps")

            def open_email(e) -> None:
                if not admin:
                    return
                user = next((u for u in list_users() if u["id"] == e.args.get("id")), None)
                if user is None or user["email"]:
                    return
                email_target[0] = user["id"]
                email_name.set_text(user["username"])
                address.set_value("")
                address_error.set_text("")
                email_dialog.open()

        with ui.row().classes("w-full items-center justify-between users-table-heading"):
            ui.label("All users").classes("text-xl")
            table_count = ui.label("").classes("users-table-count")

        # ── User table ────────────────────────────────────────────────────────
        cols = [
            {"name": "username",   "label": t("users_col_username"),
             "field": "username",   "sortable": True, "align": "left"},
            {"name": "email", "label": "Email address", "field": "email", "align": "left"},
            {"name": "role",       "label": t("users_col_role"),
             "field": "role",       "sortable": True, "align": "left"},
            {"name": "is_active",  "label": t("users_col_status"),
             "field": "is_active",  "sortable": True, "align": "left"},
            {"name": "created_at", "label": t("users_col_created"),
             "field": "created_at", "sortable": True, "align": "left"},
            {"name": "actions",    "label": "",
             "field": "id",         "align": "right"},
        ]
        tbl = ui.table(columns=cols, rows=[], row_key="id").classes("w-full")
        tbl.props("dense flat bordered")

        tbl.add_slot("body-cell-role", """
            <q-td :props="props">
                <q-badge :color="props.row.role === 'admin'    ? 'grey-8'    :
                                 props.row.role === 'teacher'  ? 'orange' : 'blue'">
                    {{ props.row.role }}
                </q-badge>
            </q-td>
        """)

        tbl.add_slot("body-cell-is_active", """
            <q-td :props="props">
                <q-badge :color="props.row.is_active ? 'green' : 'grey'">
                    {{ props.row.is_active ? '""" + t("users_status_active") + """' : '""" + t("users_status_inactive") + """' }}
                </q-badge>
            </q-td>
        """)

        if admin:
            tbl.add_slot("body-cell-actions", """
                <q-td :props="props">
                    <q-btn v-if="!props.row.email" flat dense round icon="alternate_email"
                        aria-label="Add email" @click="$parent.$emit('add_email', props.row)">
                        <q-tooltip>Add sign-in email</q-tooltip>
                    </q-btn>
                    <q-btn
                        v-if="props.row.role === 'student' && !props.row.is_active"
                        flat dense round icon="lock_open" color="primary" aria-label="Activate account"
                        @click="$parent.$emit('activate_user', props.row)"
                    />
                    <q-btn
                        v-if="props.row.role !== 'admin'"
                        flat dense round icon="delete" color="red" aria-label="Delete user"
                        @click="$parent.$emit('delete_user', props.row)"
                    />
                </q-td>
            """)
        else:
            tbl.add_slot("body-cell-actions", """
                <q-td :props="props">
                    <q-btn
                        v-if="props.row.role === 'student' && !props.row.is_active"
                        flat dense round icon="lock_open" color="primary" aria-label="Activate account"
                        @click="$parent.$emit('activate_user', props.row)"
                    />
                    <q-btn
                        v-if="props.row.role === 'student'"
                        flat dense round icon="delete" color="red" aria-label="Delete user"
                        @click="$parent.$emit('delete_user', props.row)"
                    />
                </q-td>
            """)

        async def handle_delete(e) -> None:
            row  = e.args
            uid  = row.get("id")
            role = row.get("role", "")
            uname = row.get("username", str(uid))
            if not uid or int(uid) == current["id"]:
                return
            can_delete = (
                (admin and role in ("teacher", "student")) or
                (not admin and role == "student")
            )
            if not can_delete:
                return
            # Remove from table immediately so the user can't double-click
            tbl.rows = [r for r in tbl.rows if r.get("id") != uid]
            tbl.update()
            client = _ctx.client
            asyncio.create_task(_delete_user_bg(int(uid), uname, client))

        tbl.on("delete_user", handle_delete)
        if admin:
            tbl.on("add_email", open_email)

        # ── Set password / activate dialog ────────────────────────────────────
        _activate_row: list[dict] = [{}]
        with ui.dialog() as activate_dialog, ui.card().classes("w-96"):
            ui.label(t("users_activate_title")).classes("text-base font-semibold mb-2")
            activate_name_lbl = ui.label("").classes(
                "font-mono text-sm text-yellow-600 dark:text-yellow-300 mb-1")
            act_email = ui.input(t("staff_email")).props("type=email outlined dense")
            act_pwd = new_password_field(t("users_temp_password")).classes("w-full")
            act_msg  = ui.label("").classes("text-sm")
            with ui.row().classes("gap-2 mt-2"):
                async def do_activate() -> None:
                    pwd = act_pwd.value
                    if len(pwd) < MIN_PASSWORD_LENGTH:
                        act_msg.set_text(
                            t("pwd_err_short").format(n=MIN_PASSWORD_LENGTH))
                        act_msg.classes(replace="text-sm text-red-500")
                        return
                    uid = _activate_row[0].get("id")
                    if not uid:
                        return
                    loop = asyncio.get_event_loop()
                    try:
                        await loop.run_in_executor(
                            None, lambda: activate_user(int(uid), pwd, email=act_email.value)
                        )
                        act_msg.set_text(t("users_activated").format(
                            uname=_activate_row[0].get("username", "")))
                        act_msg.classes(replace="text-sm text-green-600")
                        act_pwd.set_value("")
                        _refresh()
                    except Exception as e:
                        act_msg.set_text(t("users_error").format(e=e))
                        act_msg.classes(replace="text-sm text-red-500")

                ui.button(t("users_activate_btn"), on_click=do_activate).props(
                    "color=primary dense")
                ui.button(t("users_create_section_cancel"), on_click=activate_dialog.close).props(
                    "flat dense")

        def handle_activate(e) -> None:
            row = e.args
            _activate_row[0] = row
            act_email.set_value(next((u["email"] for u in list_users() if u["id"] == row["id"]), "") or "")
            activate_name_lbl.set_text(row.get("username", ""))
            act_pwd.set_value("")
            act_msg.set_text("")
            activate_dialog.open()

        tbl.on("activate_user", handle_activate)

    def _refresh() -> None:
        users = list_users()
        active_count = sum(bool(user["is_active"]) for user in users)
        totals["total"].set_text(str(len(users)))
        totals["active"].set_text(str(active_count))
        totals["teachers"].set_text(str(sum(user["role"] == "teacher" for user in users)))
        totals["students"].set_text(str(sum(user["role"] == "student" for user in users)))
        inactive_count = len(users) - active_count
        inactive_note.set_text(f"{inactive_count} inactive account" + ("" if inactive_count == 1 else "s"))
        table_count.set_text(f"{len(users)} account" + ("" if len(users) == 1 else "s"))
        tbl.rows = [{k: v for k, v in user.items() if k in {"id", "username", "email", "role", "is_active", "created_at"}}
                    for user in users]
        tbl.update()

    _refresh()

    # ── Background tasks ──────────────────────────────────────────────────────

    async def _assign_events_bg(
        user_id: int, username: str, msg_label: ui.label, client,
    ) -> None:
        """Assign historical events to a newly created student in the background."""
        loop = asyncio.get_event_loop()
        try:
            n = await loop.run_in_executor(
                None, lambda: auto_assign_user_events(username, user_id)
            )
            with client:
                if n:
                    msg_label.set_text(
                        t("users_auto_assigned_done").format(uname=username, n=n))
                else:
                    msg_label.set_text(
                        t("users_created_student").format(uname=username, suffix=""))
        except Exception:
            pass  # non-critical — user was already created successfully

    async def _delete_user_bg(user_id: int, username: str, client) -> None:
        """Nullify events in batches then delete the user row."""
        loop = asyncio.get_event_loop()
        with client:
            notif = toast(
                t("users_deleting_bg").format(uname=username),
                type="ongoing", spinner=True, timeout=5000,
            )
        try:
            await loop.run_in_executor(
                None, lambda: nullify_user_events(user_id)
            )
            await loop.run_in_executor(
                None, lambda: delete_user(user_id)
            )
            with client:
                if notif is not None:
                    notif.dismiss()
                toast(t("users_deleted"), type="warning", timeout=5000)
                _refresh()
        except Exception as ex:
            with client:
                if notif is not None:
                    notif.dismiss()
                toast(t("users_delete_failed").format(e=ex), type="negative", timeout=5000)
                _refresh()  # re-add the row if delete failed
