"""Teacher alerts: asynchronous loading, explicit read actions and shared screenshots."""
import asyncio
import logging
import time
from nicegui import run, ui
from backend.db.notifications import list_notifications, notification_status, mark_read, mark_all_read
from backend.db.database import get_event_frame_b64, get_event_frame_annotated_b64
from frontend.pages._snapshot import make_snapshot_dialogs
from frontend.pages.design_assets import stylesheet
from frontend.pages.admin_shell import toast


class NotificationPanel:
    def __init__(self):
        stylesheet('notifications.css')
        self.lock = asyncio.Lock()
        self.cursor = None
        self.signature = None
        self.cooldowns = {}
        self.snapshot_busy = False
        _, _, self.show_snapshot = make_snapshot_dialogs()
        with ui.dialog().props('position=right transition-show=slide-left transition-hide=slide-right') as self.dialog:
            with ui.card().classes('notification-panel'):
                with ui.row().classes('notification-heading w-full items-center justify-between'):
                    with ui.column().classes('gap-1'):
                        ui.label('Notifications').classes('notification-title')
                        self.summary = ui.label('Checking alerts…').classes('notification-muted')
                    ui.button(icon='close',on_click=self.dialog.close).props('flat round aria-label="Close notifications"')
                with ui.row().classes('notification-actions w-full'):
                    self.mark_all = ui.button('Mark all as read',icon='done_all',on_click=self.read_all).props('flat no-caps')
                    ui.button(icon='refresh',on_click=self.reload).props('flat round aria-label="Refresh notifications"')
                self.body = ui.column().classes('notification-list w-full').props('aria-label="Alert list"')
                with self.body:
                    ui.spinner(size='28px',color='white')
                    ui.label('Loading alerts…').classes('notification-muted')
                ui.label('Showing the latest 60 alerts.').classes('notification-footer')
        self.dialog.on('show',self.reload)
        with ui.button(icon='notifications',on_click=self.dialog.open).props('flat round color=white aria-label="Notifications"'):
            self.badge = ui.badge('').props('floating').classes('notification-count')
            self.badge.set_visibility(False)
        ui.timer(0.05,self.refresh,once=True)
        ui.timer(3,self.refresh)

    async def reload(self):
        await self.refresh(force=True)

    async def refresh(self,force=False):
        with self.dialog:
            if self.lock.locked() and not force:
                return
            async with self.lock:
                try:
                    status = await run.io_bound(notification_status)
                    latest = status['latest']
                    if self.cursor is not None and latest > self.cursor:
                        arrivals = await run.io_bound(list_notifications,60,self.cursor)
                        self.announce([n for n in arrivals if not n['is_read']])
                        latest = max([latest]+[n['id'] for n in arrivals])
                    self.cursor = latest if self.cursor is None else max(self.cursor,latest)
                    count = status['unread']
                    self.badge.set_text(str(count) if count < 100 else '99+')
                    self.badge.set_visibility(count > 0)
                    self.summary.set_text(f'{count} unread' if count else 'You’re all caught up')
                    self.mark_all.set_enabled(count > 0)
                    if self.dialog.value or force:
                        items = await run.io_bound(list_notifications)
                        signature = [(n['id'],n['is_read'],n['has_frame']) for n in items]
                        if force or signature != self.signature:
                            self.render(items)
                            self.signature = signature
                except Exception:
                    logging.getLogger(__name__).exception('Notification refresh failed')
                    if force:
                        self.body.clear()
                        with self.body:
                            ui.icon('cloud_off').classes('notification-empty-icon')
                            ui.label('Alerts could not load. Please try again.').props('role=alert')
                            ui.button('Try again',icon='refresh',on_click=self.reload).props('no-caps')

    def render(self,items):
        # Keep the reading position when new alerts arrive.
        with self.dialog:
            ui.run_javascript(f"window['notificationScroll{self.body.id}']=document.getElementById('{self.body.html_id}')?.scrollTop||0")
            self.body.clear()
            with self.body:
                if not items:
                    with ui.column().classes('notification-empty w-full items-center'):
                        ui.icon('notifications_none').classes('notification-empty-icon')
                        ui.label('No alerts yet').classes('notification-row-title')
                        ui.label('New monitoring alerts will appear here.').classes('notification-muted')
                for item in items:
                    self.render_row(item)
            ui.run_javascript(f"requestAnimationFrame(()=>{{const el=document.getElementById('{self.body.html_id}');if(el)el.scrollTop=window['notificationScroll{self.body.id}']||0}})")

    def render_row(self,item):
        unread = not item['is_read']
        with ui.card().classes('notification-item'+(' is-unread' if unread else '')).props(f'data-notification-id={item["id"]}'):
            with ui.row().classes('items-center justify-between w-full gap-2'):
                ui.label(item['class_name']).classes('notification-row-title')
                ui.label('Unread' if unread else 'Read').classes('notification-read-state')
            for icon,key in [('computer','computer'),('person_outline','student'),('schedule','created_at')]:
                with ui.row().classes('notification-metadata items-center gap-2'):
                    ui.icon(icon)
                    ui.label(item[key])
            with ui.row().classes('notification-row-actions w-full items-center'):
                if item['has_frame']:
                    ui.button('View screenshot',icon='image',on_click=lambda n=item:self.view(n)).props('outline no-caps')
                else:
                    ui.label('Screenshot unavailable').classes('notification-muted')
                if unread:
                    ui.button('Mark as read',icon='done',on_click=lambda n=item:self.read(n['id'])).props('flat no-caps')

    async def read(self,notification_id):
        with self.dialog:
            try:
                await run.io_bound(mark_read,notification_id)
                await self.reload()
            except Exception:
                toast('Could not mark this alert as read. Please try again.',type='negative')

    async def read_all(self):
        with self.dialog:
            self.mark_all.props('loading')
            try:
                await run.io_bound(mark_all_read)
                await self.reload()
            except Exception:
                toast('Could not mark alerts as read. Please try again.',type='negative')
            finally:
                self.mark_all.props(remove='loading')

    async def view(self,item):
        with self.dialog:
            if self.snapshot_busy:
                return
            self.snapshot_busy = True
            loading = toast('Loading screenshot…',timeout=0,spinner=True)
            try:
                raw = await run.io_bound(get_event_frame_b64,item['event_id'])
                if not raw:
                    toast('This screenshot is no longer available.',type='warning')
                    return
                annotated = await run.io_bound(get_event_frame_annotated_b64,item['event_id'])
                await run.io_bound(mark_read,item['id'])
                await self.reload()
                self.show_snapshot(raw,' • '.join(str(item[k]) for k in ('class_name','computer','student','created_at')),annotated)
            except Exception:
                logging.getLogger(__name__).exception('Notification screenshot failed')
                toast('The screenshot could not load. Please try again.',type='negative')
            finally:
                loading.dismiss()
                self.snapshot_busy = False

    def announce(self,items):
        with self.dialog:
            from frontend.pages.notification_sound import play_alert_sound
            now = time.monotonic()
            shown = 0
            for item in items:
                computer = item['computer']
                if now-self.cooldowns.get(computer,-100) < 5:
                    continue
                self.cooldowns[computer] = now
                if not self.dialog.value:
                    toast(f"{item['class_name']} detected — {computer} • {item['student']}",type='warning',timeout=8000,close_button=True)
                shown += 1
                if shown == 3:
                    break
            if shown:
                play_alert_sound()


def notification_bell():
    return NotificationPanel()
