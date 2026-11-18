"""Editor choices resolved in a worker, including older models needing class sync."""
from backend.db._core import _conn
from backend.db.database import list_groups, list_models, get_active_model, get_schedule, sync_classes_from_model


def editor_choices(schedule_id=None):
    models = list_models()
    c = _conn()
    mapped = {r[0] for r in c.execute('SELECT DISTINCT model_id FROM model_class')}
    for model in models:
        if model['id'] not in mapped:
            sync_classes_from_model(model['id'])
    by_model = {}
    for row in c.execute('SELECT mc.model_id,dc.id,dc.name FROM model_class mc JOIN detection_class dc '
                         'ON dc.id=mc.class_id ORDER BY mc.model_id,mc.class_index'):
        by_model.setdefault(row[0], []).append({'id': row[1], 'name': row[2]})
    schedule = get_schedule(schedule_id) if schedule_id is not None else None
    if schedule_id is not None and schedule is None:
        raise ValueError('This schedule no longer exists. Refresh the page.')
    return {'groups': list_groups(), 'models': models, 'active': get_active_model(),
            'classes': by_model, 'schedule': schedule}
