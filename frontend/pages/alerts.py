"""Teacher alert rules with model scoping and schedule-aware glass controls."""
import logging
from nicegui import run, ui
from backend.core.auth import require_auth
from frontend.pages._nav import nav
from frontend.pages.admin_shell import toast
from frontend.pages.alert_rule_data import load_context, save_global_rule
from frontend.pages.alert_rule_row import class_row
from frontend.pages.design_assets import stylesheet
from frontend.pages.glass_fields import text_field
from frontend.translate import t


@ui.page('/alerts')
def page_alerts():
    current = require_auth(required_role='teacher')
    if current is None:
        return
    nav(current)
    stylesheet('alert-rules.css')
    view = {'context': None, 'loading': False, 'saving': 0, 'needs_refresh': False}
    rows = []
    with ui.column().classes('alerts-dashboard w-full'):
        with ui.column().classes('alerts-heading'):
            ui.label(t('alerts_title')).classes('alerts-title')
            ui.label('Choose which detected classes should raise an alert.').classes('alerts-subtitle')
        with ui.card().classes('alerts-explainer w-full'):
            ui.icon('info_outline').classes('alerts-section-icon')
            with ui.column().classes('alerts-explainer-copy'):
                ui.label('Prohibited classes can trigger alerts during monitoring.').classes('alerts-explainer-title')
                ui.label('Allowed classes still appear in History. The repeat-detection threshold in Settings controls when alerts are raised.').classes('alerts-help')
        with ui.element('div').classes('alerts-stats w-full'):
            counts = []
            for label, icon in [('Classes shown', 'category'), ('Prohibited', 'notifications_active'), ('Allowed', 'notifications_off')]:
                with ui.card().classes('alerts-stat-card user-stat-card'):
                    with ui.row().classes('w-full items-center justify-between gap-3'):
                        ui.label(label).classes('alerts-stat-label')
                        ui.icon(icon).classes('alerts-section-icon')
                    counts.append(ui.label('—').classes('alerts-stat-value'))
        with ui.card().classes('alerts-toolbar w-full'):
            with ui.column().classes('alerts-model-copy'):
                model_label = ui.label('Loading detection classes...').classes('alerts-section-title')
                model_hint = ui.label('').classes('alerts-help')
            refresh_btn = ui.button('Refresh', icon='refresh', on_click=lambda: refresh()).props('no-caps')
        with ui.card().classes('alerts-schedule-note w-full') as schedule_note:
            ui.icon('lock_outline').classes('alerts-section-icon')
            ui.label(t('alerts_schedule_override_note')).classes('alerts-help')
        schedule_note.set_visibility(False)
        search = text_field('Find a class', icon='search', placeholder='Search detection classes', props='debounce=150')
        with ui.column().classes('alerts-rules w-full') as rules_list:
            for _ in range(3):
                ui.skeleton().classes('alerts-loading w-full')
        with ui.column().classes('alerts-empty items-center w-full') as empty:
            ui.icon('manage_search').classes('alerts-empty-icon')
            empty_title = ui.label('No matching classes').classes('alerts-empty-title')
            empty_hint = ui.label('Try a different class name.').classes('alerts-help')
        empty.set_visibility(False)
        ui.label(t('alerts_changes_note')).classes('alerts-help')

    def update_counts():
        context = view['context']
        if not context:
            return
        rules = context['rules']
        prohibited = sum(bool(r['effective_enabled']) for r in rules)
        for label, value in zip(counts, [len(rules), prohibited, len(rules) - prohibited]):
            label.set_text(str(value))

    def filter_rows():
        query = (search.value or '').strip().casefold()
        visible = 0
        for name, card in rows:
            show = query in name.casefold()
            card.set_visibility(show)
            visible += show
        empty.set_visibility(not visible and not view['loading'])

    async def save(class_id, enabled):
        context = view['context']
        if view['loading'] or context is None:
            return False
        view['saving'] += 1
        refresh_btn.props('disable')
        try:
            try:
                await run.io_bound(save_global_rule, class_id, enabled, context['signature'])
            except ValueError as exc:
                toast(str(exc), type='warning')
                view['needs_refresh'] = True
                return False
            except Exception:
                logging.getLogger(__name__).exception('Alert rule save failed')
                toast('The change could not be saved. Your previous rule is still shown. Try again.', type='negative')
                return False
            rule = next(r for r in context['rules'] if r['class_id'] == class_id)
            rule['enabled'] = rule['effective_enabled'] = enabled
            update_counts()
            toast(t('alerts_enabled_for' if enabled else 'alerts_disabled_for').format(name=rule['name']), type='positive')
            return True
        finally:
            view['saving'] -= 1
            if not view['saving']:
                refresh_btn.props(remove='disable')
                if view['needs_refresh']:
                    view['needs_refresh'] = False
                    ui.timer(0.05, refresh, once=True)

    async def refresh():
        if view['loading'] or view['saving']:
            return
        view['loading'] = True
        refresh_btn.props('loading')
        try:
            context = await run.io_bound(load_context)
            view['context'] = context
            active = context['active']
            model_label.set_text(f"Classes for {active['name']}" if active else 'All detection classes')
            model_hint.set_text('Currently running model.' if context['running_override'] else
                                ('Rules for this model.' if active else 'No active model. Showing all saved detection classes.'))
            schedule_note.set_visibility(context['readonly'])
            rules_list.clear()
            rows.clear()
            with rules_list:
                for rule in context['rules']:
                    rows.append((rule['name'], class_row(rule, readonly=context['readonly'], save=save)))
            empty_title.set_text('No matching classes' if context['rules'] else 'No detection classes yet')
            empty_hint.set_text('Try a different class name.' if context['rules'] else
                                (t('alerts_none_active') if active else t('alerts_none_any')))
            update_counts()
        except Exception:
            logging.getLogger(__name__).exception('Alert rules could not load')
            if view['context'] is None:
                rules_list.clear()
                model_label.set_text('Detection classes unavailable')
                model_hint.set_text('Refresh to try loading the rules again.')
                empty_title.set_text('Rules could not load')
                empty_hint.set_text('Use Refresh to try again.')
            toast('Alert rules could not load. Please refresh and try again.', type='negative')
        finally:
            view['loading'] = False
            refresh_btn.props(remove='loading')
            filter_rows()

    search.on_value_change(filter_rows)
    ui.timer(0.01, refresh, once=True)
