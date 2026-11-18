"""Resolve the model and alert policy currently shown to a teacher."""
import backend.state as state
from backend.db.database import (get_active_model, get_model_by_id, get_prohibited_class_ids,
                                 get_schedule, list_alert_rules, set_alert_rule)


def load_context():
    with state.monitor_lock:
        monitor = state.monitor
        running_mid = state.running_model_id if monitor else None
        schedule_id = getattr(monitor, 'schedule_id', None) if monitor else None
    db_active = get_active_model()
    running_override = running_mid is not None and running_mid != (db_active or {}).get('id')
    active = get_model_by_id(running_mid) if running_override else db_active
    schedule = get_schedule(schedule_id) if monitor and schedule_id is not None else None
    readonly = bool(schedule and schedule.get('use_custom_notify_classes') and running_mid is not None)
    effective = None
    if monitor and running_mid is not None:
        effective = {v['id'] for v in get_prohibited_class_ids(running_mid, schedule_id).values()}
    names = {n.strip() for n in active.get('class_names', [])} if active else None
    rules = [r for r in list_alert_rules() if names is None or r['name'] in names]
    for rule in rules:
        rule['effective_enabled'] = rule['class_id'] in effective if effective is not None else bool(rule['enabled'])
    return {'active': active, 'running_override': running_override, 'readonly': readonly, 'rules': rules,
            'signature': (id(monitor), running_mid, (active or {}).get('id'), schedule_id, readonly)}


def save_global_rule(class_id, enabled, expected_signature):
    context = load_context()
    if context['signature'] != expected_signature:
        raise ValueError('The active model or schedule changed. Review the refreshed rules and try again.')
    if context['readonly']:
        raise ValueError('This exam uses schedule rules. Edit the schedule to change them.')
    if not any(r['class_id'] == class_id for r in context['rules']):
        raise ValueError('This class is no longer available. Review the refreshed rules.')
    set_alert_rule(class_id, enabled)
