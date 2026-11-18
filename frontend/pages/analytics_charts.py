"""Neutral chart styling and empty states for the analytics dashboard."""
from nicegui import ui
from frontend.translate import t

PALETTE = ['#ededed', '#aaa', '#747474', '#505050', '#cecece', '#909090']


def _base():
    return {'backgroundColor': 'transparent', 'color': PALETTE,
            'textStyle': {'color': '#ccc', 'fontFamily': 'Segoe UI, sans-serif'},
            'animationDuration': 700, 'animationDurationUpdate': 450,
            'aria': {'enabled': True},
            'tooltip': {'backgroundColor': '#202020ed', 'borderColor': '#ffffff40',
                        'textStyle': {'color': '#eee'}, 'confine': True}}


def chart_card(title, icon, hint, options, classes=''):
    with ui.card().classes('analytics-chart-card ' + classes):
        with ui.row().classes('items-center gap-3'):
            ui.icon(icon).classes('analytics-section-icon')
            ui.label(title).classes('analytics-section-title')
        ui.label(hint).classes('analytics-chart-hint')
        base = _base()
        tooltip = options.pop('tooltip', {})
        base['tooltip'].update(tooltip)
        base.update(options)
        chart = ui.echart(base).classes('analytics-chart w-full').props(f'aria-label="{title}"').style('height:330px')
        chart.set_visibility(False)
        with ui.column().classes('analytics-chart-empty items-center justify-center w-full') as empty:
            ui.icon('insert_chart_outlined').classes('analytics-empty-icon')
            ui.label('No activity in this selection').classes('analytics-empty-title')
            ui.label('Choose another date range or filter to see results.')
        empty.set_visibility(False)
    return chart, empty


def distribution_chart():
    return chart_card(t('analytics_class_dist'), 'donut_large',
                      'Number of detections for each class.', {
        'tooltip': {'trigger': 'item', 'formatter': '{b}: {c} ({d}%)'},
        'legend': {'type': 'scroll', 'bottom': 0, 'textStyle': {'color': '#ccc'}},
        'series': [{'type': 'pie', 'radius': ['42%', '66%'], 'center': ['50%', '43%'],
                    'label': {'show': False}, 'itemStyle': {'borderColor': '#111', 'borderWidth': 3},
                    'emphasis': {'label': {'show': True, 'color': '#eee'}}, 'data': []}],
    })


def activity_chart(students=False):
    title = t('analytics_student_hits') if students else t('analytics_daily_activity')
    category = {'type': 'category', 'data': [], 'axisLabel': {'color': '#bbb', 'hideOverlap': True},
                'axisLine': {'lineStyle': {'color': '#ffffff30'}}}
    value = {'type': 'value', 'minInterval': 1, 'axisLabel': {'color': '#aaa'},
             'splitLine': {'lineStyle': {'color': '#ffffff10'}}}
    series = [{'name': t('analytics_detections'), 'type': 'bar', 'data': [],
               'barMaxWidth': 22, 'itemStyle': {'color': '#bababa', 'borderRadius': 4}}]
    if students:
        category.update(inverse=True, axisLabel={'color': '#ccc', 'width': 125, 'overflow': 'truncate'})
    else:
        category['axisLabel']['formatter'] = '{value}'
        series.insert(0, {'name': t('analytics_all_events'), 'type': 'bar', 'data': [],
                          'barMaxWidth': 22, 'itemStyle': {'color': '#ededed', 'borderRadius': [4, 4, 0, 0]}})
    return chart_card(title, 'people_outline' if students else 'bar_chart',
                      'Detection events by student. Uses the filters above.' if students else
                      'Compare all captured events with events containing detections.', {
        'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'shadow'}},
        'legend': {'show': not students, 'top': 0, 'textStyle': {'color': '#ccc'}},
        'grid': {'left': 12, 'right': 20, 'top': 42, 'bottom': 20, 'containLabel': True},
        'xAxis': value if students else category, 'yAxis': category if students else value,
        'series': series,
    }, 'analytics-student-chart' if students else '')
