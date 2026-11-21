"""One Veyon import operation shared by the React API and legacy interface."""
from backend.core.veyon import list_locations
from backend.db.database import get_or_create_group, upsert_computer, add_computer_to_group, log_action


def import_locations(cli, user_id):
    locations = list_locations(cli)
    count = 0
    for location in locations:
        gid = get_or_create_group(location['name'], 'Imported from Veyon location')
        for computer in location['computers']:
            cid = upsert_computer(computer['name'], computer['host'])
            add_computer_to_group(cid, gid)
            count += 1
    if locations:
        log_action('group.import_veyon', user_id=user_id, detail=f'{len(locations)} groups, {count} computers')
    return len(locations), count
