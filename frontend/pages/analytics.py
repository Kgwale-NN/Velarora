"""Teacher and student analytics with matching glass controls and async queries."""
from __future__ import annotations

import logging
from datetime import date, timedelta
from nicegui import run, ui
from backend.core.auth import require_auth
from backend.db.database import (get_class_distribution, get_daily_detections,
    get_student_activity, get_summary_stats, list_computers, list_users)
from frontend.pages._nav import nav
from frontend.pages.admin_shell import toast
from frontend.pages.analytics_charts import activity_chart, distribution_chart
from frontend.pages.design_assets import stylesheet
from frontend.pages.glass_fields import select_field, text_field
from frontend.translate import t


@ui.page('/analytics')
def page_analytics():
    current = require_auth()
    if current is None:
        return
    nav(current)
    teacher = current['role'] == 'teacher'
    stylesheet('analytics.css')
    busy = [False]

    with ui.column().classes('analytics-dashboard w-full') as dashboard:
        with ui.column().classes('analytics-heading'):
            ui.label(t('analytics_title')).classes('analytics-title')
            ui.label('See how computers are used and review detection patterns.').classes('analytics-subtitle')
        with ui.card().classes('analytics-filters w-full'):
            with ui.row().classes('items-center gap-3'):
                ui.icon('tune').classes('analytics-section-icon')
                ui.label('Choose what to review').classes('analytics-section-title')
            with ui.element('div').classes('analytics-filter-grid w-full'):
                today = date.today()
                f_from = text_field(t('analytics_from'), value=(today - timedelta(days=29)).isoformat(),
                                    icon='calendar_today', props='type=date')
                f_to = text_field(t('analytics_to'), value=today.isoformat(),
                                  icon='event', props='type=date')
                if teacher:
                    computers = {'': t('analytics_all_computers')}
                    computers.update({str(c['id']): c['name'] for c in list_computers()})
                    students = {'': t('analytics_all_students')}
                    students.update({str(u['id']): u['username'] for u in list_users() if u['role'] == 'student'})
                    f_computer = select_field(t('analytics_computer'), computers, value='', icon='computer')
                    f_student = select_field(t('analytics_student'), students, value='', icon='person_outline')
            with ui.row().classes('w-full justify-end'):
                apply_btn = ui.button(t('analytics_apply'), icon='filter_alt', on_click=lambda: refresh()).props('no-caps')
        scope = ui.label('Loading analytics...').classes('analytics-scope').props('role=status aria-live=polite')
        with ui.element('div').classes('analytics-stats w-full'):
            cards = [_stat_card(t(label), icon) for label, icon in [
                ('analytics_total_events', 'desktop_windows'), ('analytics_detection_events', 'find_in_page'),
                ('analytics_active_students', 'people_outline'), ('analytics_most_detected', 'category')]]
        with ui.element('div').classes('analytics-chart-grid w-full'):
            donut, donut_empty = distribution_chart()
            daily_chart, daily_empty = activity_chart()
        students_chart, students_empty = activity_chart(students=True) if teacher else (None, None)

    def load_data(cid, uid, fd, td):
        return (get_summary_stats(cid, uid, fd, td), get_class_distribution(cid, uid, fd, td),
                get_daily_detections(cid, uid, fd, td),
                get_student_activity(cid, fd, td, user_id=uid) if teacher else [])

    async def refresh():
        if busy[0]:
            return
        fd, td = f_from.value or '', f_to.value or ''
        try:
            for value in (fd, td):
                if value:
                    date.fromisoformat(value)
        except ValueError:
            toast('Choose a valid start and end date.', type='warning')
            return
        if fd and td and fd > td:
            toast(t('analytics_err_date_range'), type='warning')
            return
        cid = int(f_computer.value) if teacher and f_computer.value else None
        uid = (int(f_student.value) if f_student.value else None) if teacher else current['id']
        caption = f"{fd or 'Any start date'} to {td or 'Any end date'}"
        if teacher:
            caption += f" · {computers[f_computer.value]} · {students[f_student.value]}"
        busy[0] = True
        apply_btn.props('loading')
        dashboard.props('aria-busy=true')
        try:
            stats, dist, daily, activity = await run.io_bound(load_data, cid, uid, fd, td)
            for card, key in zip(cards, ['total_events', 'detection_events', 'active_students', 'top_class']):
                card['value'].set_text(str(stats[key]))
                card['loading'].set_visibility(False)
                card['value'].set_visibility(True)
            donut.options['series'][0]['data'] = [{'name': d['name'], 'value': d['count']} for d in dist]
            _show_chart(donut, donut_empty, bool(dist))
            daily_chart.options['xAxis']['data'] = [r['day'] for r in daily]
            daily_chart.options['series'][0]['data'] = [r['total'] for r in daily]
            daily_chart.options['series'][1]['data'] = [r['hits'] for r in daily]
            _show_chart(daily_chart, daily_empty, bool(daily))
            if students_chart is not None:
                students_chart.options['yAxis']['data'] = [r['student'] for r in activity]
                students_chart.options['series'][0]['data'] = [r['hits'] for r in activity]
                students_chart.style(f'height:{max(330, len(activity) * 34 + 65)}px')
                _show_chart(students_chart, students_empty, bool(activity))
            scope.set_text(caption)
        except Exception:
            logging.getLogger(__name__).exception('Analytics refresh failed')
            toast('Analytics could not load. Please try again.', type='negative')
            scope.set_text('Could not update analytics. Try applying your filters again.')
            for card in cards:
                card['loading'].set_visibility(False)
                card['value'].set_visibility(True)
        finally:
            busy[0] = False
            apply_btn.props(remove='loading')
            dashboard.props('aria-busy=false')

    ui.timer(0.01, refresh, once=True)


def _show_chart(chart, empty, has_data):
    chart.set_visibility(has_data)
    empty.set_visibility(not has_data)
    chart.update()


def _stat_card(label, icon):
    with ui.card().classes('analytics-stat-card user-stat-card'):
        with ui.row().classes('w-full items-center justify-between gap-3'):
            ui.label(label).classes('analytics-stat-label')
            ui.icon(icon).classes('analytics-section-icon')
        loading = ui.skeleton().classes('analytics-stat-loading')
        value = ui.label('—').classes('analytics-stat-value')
        value.set_visibility(False)
    return {'value': value, 'loading': loading}
